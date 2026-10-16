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
import io
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
    parser.add_argument("--self-test", action="store_true",
                        help="prove the verifier can fail (offline, no device)")
    args = parser.parse_args(argv)

    repo_root = args.root or find_repo_root(__file__)
    if not repo_root:
        print("cannot locate the Nuxel repository root; pass --root", file=sys.stderr)
        return EXIT_USAGE

    if args.self_test:
        print("verify-permissions.py self-test  root=%s" % repo_root)
        return self_test(repo_root)

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


# ---------------------------------------------------------------------------
# Self-test: proves the verifier can FAIL, not just that it can print PASS.
# ---------------------------------------------------------------------------
def _quiet_main(argv):
    """Run main() capturing its exit code (output is suppressed)."""
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = main(argv)
    return rc, buf.getvalue()


def self_test(repo_root):
    import shutil
    import tempfile

    failures = []

    def check(name, cond, detail=""):
        print("  %-4s %s%s" % ("PASS" if cond else "FAIL", name,
                               "" if cond else "  <- " + str(detail)))
        if not cond:
            failures.append(name)

    fixture = os.path.join(repo_root, "tools", "s10plus", "a33",
                           "security-fixtures", "s10plus-4.14.253.json")
    if not os.path.isfile(fixture):
        print("self-test requires %s" % fixture, file=sys.stderr)
        return EXIT_USAGE

    permd = load_permd(repo_root)
    registry = permd.Registry()
    facts = permd.kernel_facts(fixture, None)
    tmp = tempfile.mkdtemp(prefix="verify-permissions-selftest-")
    try:
        # 1. The fixture must actually downgrade the impossible mechanisms. If a
        #    fixture ever claimed Landlock on 4.14 the tool would be lying.
        avail = facts.get("mechanism_availability", {})
        check("fixture reports landlock unavailable on 4.14",
              avail.get("landlock") in ("no", "unavailable", None), avail.get("landlock"))
        check("fixture reports nft socket cgroupv2 unavailable",
              avail.get("nft_socket_cgroupv2") in ("no", "unavailable", None),
              avail.get("nft_socket_cgroupv2"))

        # 2. Every capability in the registry names an attacker class and a
        #    limitation. This is the "no claim without a scope" invariant.
        bad = []
        for row in registry.matrix():
            if not row.get("limitation"):
                bad.append(row["id"])
            if row.get("grant_required", True) and row.get("enforces_against") not in (
                    "unprivileged-app", "some-apps", "nobody"):
                bad.append(row["id"])
        check("every capability carries a limitation and a scope", not bad, bad)

        # 3. Repository mode on an empty store: no hard errors (a checkout
        #    legitimately has no grants) and no unregistered tokens.
        rc, out = _quiet_main(["--root", repo_root, "--store", tmp, "--fixture", fixture])
        check("repo mode with an empty store passes", rc == EXIT_PASS, "exit=%s" % rc)
        check("no unregistered capability tokens remain",
              "unknown capability token" not in out, out.strip().splitlines()[:3])

        # 4. Device mode on the same empty store must FAIL: this is the
        #    fail-closed direction, and the reason the mode exists.
        rc, _ = _quiet_main(["--root", repo_root, "--store", tmp, "--fixture", fixture,
                             "--mode", "device"])
        check("device mode with no grants fails closed", rc == EXIT_MISMATCH,
              "exit=%s" % rc)

        # 5. Grant a capability that the registry says nothing enforces and
        #    pretend it is fully enforced -> must be reported as a mismatch.
        #    (This is the "cosmetic switch that lies" gate.)
        store = permd.Store(tmp, registry)
        store.write_grants("browser", {"network": {
            "granted_at": "self-test", "duration": "always",
            "portal_type": "network", "mechanisms": ["nftables"],
            "enforceable": "yes", "enforces_against": "unprivileged-app",
            "limitation": "self-test", "verdict": "OFFLINE_TESTED"}})
        rc, out = _quiet_main(["--root", repo_root, "--store", tmp, "--fixture", fixture])
        check("a grant that overstates enforcement is rejected",
              rc == EXIT_MISMATCH and "cosmetic switch" in out.lower(), "exit=%s" % rc)
        store.revoke_all("browser")

        # 6. A stored grant for a capability that nothing enforces at all
        #    (clipboard) must be refused by the store, not silently accepted.
        refused = False
        try:
            permd.Store(tmp, permd.Registry()).grant("pwa/nuxel-apps/notes", "clipboard")
        except Exception as exc:  # UnsupportedCapability or ValueError
            refused = "clipboard" in str(exc) or "cannot be enforced" in str(exc) \
                or "Unsupported" in type(exc).__name__ or "no enforcement" in str(exc)
        check("the store refuses a capability that cannot be enforced", refused)

        # 7. An unknown token is reported as unregistered (never as a grant).
        unknown = registry.resolve("totally:made-up")[0]
        check("an unknown token does not resolve", unknown is None, unknown)
        unsupported = registry.resolve("ptrace")[0]
        check("a refused token does not resolve", unsupported is None, unsupported)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    print("verify-permissions self-test %s (%d failure(s))"
          % ("PASSED" if not failures else "FAILED", len(failures)))
    return EXIT_PASS if not failures else EXIT_MISMATCH



if __name__ == "__main__":
    sys.exit(main())
