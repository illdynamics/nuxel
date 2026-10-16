#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""verify-permissions.py - cross-check every manifest's nuxel.capabilities entry
against the stored grant and against the enforcement truth (briq-05a).

It answers one question with evidence: *for every capability an app declares,
is there a durable, reviewable grant - and does that grant claim only what the
kernel can actually enforce?*

It imports the permission manager itself (shell/nuxel-shell/nuxel-permissions/
nuxel-permd.py) so the tool and the runtime can never disagree about the store
format or the enforcement matrix.

Modes
-----
  repo   (default)  Declared-but-ungranted capabilities are reported as
                    PRESENT WITHOUT GRANT and do not fail the run: a repository
                    checkout legitimately has an empty store (fail-closed).
                    Hard failures are: unsupported capability tokens, grants
                    that overstate enforcement, sandbox profiles that grant
                    what the app registry does not declare, and store/drift
                    corruption.
  device            Same checks, plus every declared capability MUST have a
                    stored grant (or be listed in --baseline). Use this on the
                    phone / in the VM image gate.

Exit codes: 0 pass, 1 mismatch, 3 unsupported capability, 4 store/registry error,
5 usage.

Examples
--------
  tools/s10plus/a33/verify-permissions.py
  tools/s10plus/a33/verify-permissions.py --mode device --store /var/lib/nuxel/permissions
  tools/s10plus/a33/verify-permissions.py --json
  tools/s10plus/a33/verify-permissions.py --fixture tools/s10plus/a33/security-fixtures/s10plus-4.14.253.json
"""

import argparse
import importlib.util
import json
import os
import sys

EXIT_PASS = 0
EXIT_MISMATCH = 1
EXIT_UNSUPPORTED = 3
EXIT_STORE = 4
EXIT_USAGE = 5


def find_repo_root(start):
    cur = os.path.abspath(start)
    while True:
        probe = os.path.join(cur, "shell", "nuxel-shell", "nuxel-permissions",
                             "nuxel-permd.py")
        if os.path.isfile(probe):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def load_permd(repo_root):
    path = os.path.join(repo_root, "shell", "nuxel-shell", "nuxel-permissions",
                        "nuxel-permd.py")
    spec = importlib.util.spec_from_file_location("nuxel_permd", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["nuxel_permd"] = module
    spec.loader.exec_module(module)
    return module


def load_baseline(path):
    if not path:
        return {}
    with open(path, "r") as fh:
        data = json.load(fh)
    # {"app-id": ["capability", ...]} or {"apps": {...}}
    return data.get("apps", data)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Cross-check manifest capabilities against stored grants "
                    "and the measured enforcement matrix")
    parser.add_argument("--root", default=None, help="repository root")
    parser.add_argument("--store", default=None,
                        help="permission store (default: NUXEL_PERMISSIONS_DIR "
                             "or /var/lib/nuxel/permissions)")
    parser.add_argument("--registry", default=None, help="capability registry JSON")
    parser.add_argument("--mode", choices=("repo", "device"), default="repo")
    parser.add_argument("--baseline", default=None,
                        help="JSON of apps/capabilities allowed to be ungranted")
    parser.add_argument("--fixture", default=None,
                        help="kernel facts fixture (offline/VM runs)")
    parser.add_argument("--config", default=None, help="kernel config file")
    parser.add_argument("--app", action="append", default=None,
                        help="limit to one app (repeatable)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--matrix", action="store_true",
                        help="also print the enforcement matrix")
    args = parser.parse_args(argv)

    repo_root = args.root or find_repo_root(__file__)
    if not repo_root:
        print("cannot locate the Nuxel repository root; pass --root", file=sys.stderr)
        return EXIT_USAGE

    try:
        permd = load_permd(repo_root)
    except Exception as exc:  # pragma: no cover - defensive
        print("cannot import nuxel-permd.py: %s" % exc, file=sys.stderr)
        return EXIT_STORE

    try:
        registry = permd.Registry(args.registry) if args.registry else permd.Registry()
    except Exception as exc:
        print("cannot load capability registry: %s" % exc, file=sys.stderr)
        return EXIT_STORE

    store = permd.Store(args.store or permd.DEFAULT_STORE, registry)

    try:
        facts = permd.kernel_facts(args.fixture, args.config)
    except Exception as exc:
        print("cannot read kernel facts: %s" % exc, file=sys.stderr)
        return EXIT_STORE

    report = permd.review(repo_root, store, registry, facts=facts,
                          require_granted=(args.mode == "device"))

    baseline = load_baseline(args.baseline)
    app_filter = set(args.app or [])

    mismatches = []
    ungranted = []
    unregistered = []
    unsupported = []

    for app in report["apps"]:
        if app_filter and app["app_id"] not in app_filter:
            continue
        allowed = set(baseline.get(app["app_id"], []))
        granted = set(app["granted"])
        for cap_id in app["declared"]:
            if cap_id in granted or cap_id in allowed:
                continue
            if not registry.enforcement_of(cap_id).get("grant_required", True):
                continue
            entry = {"app_id": app["app_id"], "capability": cap_id,
                     "reason": "declared in a manifest but no stored grant"}
            if args.mode == "device":
                mismatches.append(entry)
            else:
                ungranted.append(entry)
        for unsup in app["unsupported"]:
            entry = {"app_id": app["app_id"], "token": unsup["token"],
                     "path": unsup["path"], "reason": unsup["reason"]}
            if unsup["reason"].startswith("unsupported"):
                unsupported.append(entry)
            else:
                unregistered.append(entry)

    for finding in report["findings"]:
        if finding["severity"] != "error":
            continue
        if finding["code"] in ("declared_not_granted", "unregistered_capability"):
            continue
        mismatches.append({"app_id": finding["app_id"],
                           "capability": finding["capability"],
                           "reason": finding["code"] + ": " + finding["detail"]})

    # Enforcement honesty: a stored grant must never claim more than the
    # registry (per kernel) allows. This is the "no cosmetic switch that lies
    # about enforcement" gate.
    for app in report["apps"]:
        if app_filter and app["app_id"] not in app_filter:
            continue
        for cap_id, enf in sorted(app["enforcement"].items()):
            if not enf.get("granted"):
                continue
            if enf["enforceable"] == "yes" and enf["mechanisms"] == ["none"]:
                mismatches.append({
                    "app_id": app["app_id"], "capability": cap_id,
                    "reason": "grant claims enforcement but no mechanism exists"})
            if enf["enforces_against"] not in ("unprivileged-app", "some-apps"):
                mismatches.append({
                    "app_id": app["app_id"], "capability": cap_id,
                    "reason": "grant does not name an attacker class it holds against"})

    payload = {
        "tool": "verify-permissions.py",
        "mode": args.mode,
        "root": repo_root,
        "store": store.dir,
        "store_exists": os.path.isdir(store.dir),
        "kernel": {"release": facts.get("release"), "source": facts.get("source"),
                   "apparmor": facts.get("apparmor_enabled"),
                   "landlock": facts.get("mechanism_availability", {}).get("landlock"),
                   "nft_socket_cgroupv2":
                       facts.get("mechanism_availability", {}).get("nft_socket_cgroupv2")},
        "counts": {
            "apps": report["summary"]["apps"],
            "declared": report["summary"]["declared_capabilities"],
            "grants": report["summary"]["grants"],
            "mismatches": len(mismatches),
            "present_without_grant": len(ungranted),
            "unregistered_tokens": len(unregistered),
            "unsupported_tokens": len(unsupported),
        },
        "mismatches": mismatches,
        "present_without_grant": ungranted,
        "unregistered_tokens": unregistered,
        "unsupported_tokens": unsupported,
        "verdict": ("PASS" if (not mismatches and not unsupported) else "MISMATCH"),
    }
    if args.matrix:
        payload["enforcement_matrix"] = [
            permd.downgrade_for_kernel(row, facts) for row in registry.matrix()]

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif not args.quiet:
        print("verify-permissions.py  mode=%s  root=%s" % (args.mode, repo_root))
        print("store:  %s%s" % (store.dir, "" if payload["store_exists"] else " (absent - fail-closed)"))
        print("kernel: %s (%s) apparmor=%s landlock=%s nft_cgroupv2=%s"
              % (facts.get("release"), facts.get("source"),
                 facts.get("apparmor_enabled"),
                 facts.get("mechanism_availability", {}).get("landlock"),
                 facts.get("mechanism_availability", {}).get("nft_socket_cgroupv2")))
        print("apps=%d declared=%d grants=%d"
              % (payload["counts"]["apps"], payload["counts"]["declared"],
                 payload["counts"]["grants"]))
        for row in mismatches:
            print("MISMATCH  %-22s %-14s %s" % (row.get("app_id"), row.get("capability") or "-",
                                                row["reason"]))
        for row in unsupported:
            print("REFUSED   %-22s %-14s %s" % (row["app_id"], row["token"], row["reason"]))
        for row in unregistered:
            print("UNKNOWN   %-22s %-14s %s (fail-closed; register it in "
                  "capabilities.json)" % (row["app_id"], row["token"], row["reason"]))
        for row in ungranted:
            print("NO-GRANT  %-22s %-14s %s" % (row["app_id"], row["capability"],
                                                row["reason"]))
        print("")
        print("Verdict: %s" % payload["verdict"])

    if unsupported:
        return EXIT_UNSUPPORTED
    if mismatches:
        return EXIT_MISMATCH
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
