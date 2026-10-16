#!/usr/bin/env python3
"""suite-coverage.py — is every test in the tree reachable from the release gate?

briq-09a (area 52): `tools/beta/run-all-tests.sh` is the *only* sanctioned test
entry point, so a test file nobody runs is a test that silently rots.  This
audit reads the registry that the gate just wrote and answers one question per
discovered test artifact:

    "can the release gate reach this file?"

Reachability is transitive and deliberately generous:

  1. the file's path appears in a suite command (run directly), or
  2. a *runner* (`run-tests.sh`, `run-*-tests.sh`, `run-mock-tests.sh`) in the
     file's own directory, or up to three parent directories, appears in a
     suite command (run by a group runner), or
  3. the file lives under a directory that a suite command scans wholesale
     (`*-tests.sh`, `find … -path "*/tests/*"`), detected by matching the parent
     directory name against a command that walks that directory.

Ownership decides the verdict.  Each tree is mapped to the build group that owns
it; an orphan in a *release*-owned tree is a hard failure (this group cannot
ship a test nobody runs), while an orphan in another group's tree is reported
loudly as an integration finding but does not turn the beta gate red — those
groups are still writing into this tree while the gate runs.  `--strict-orphans`
makes every orphan fatal, which is the mode the terminal integration pass uses.

Exit codes: 0 reachable (or only non-release orphans), 1 hard failure,
2 usage/registry error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

# name patterns that mark a file as a test artifact
NAME_PATTERNS = (
    re.compile(r"^test[-_].*\.(sh|py|js|c|bash)$"),
    re.compile(r"^test.*\.(sh|py|js|c)$"),
    re.compile(r".*[-_]test\.(py|sh|js)$"),
    re.compile(r"^run-.*tests?\.sh$"),
    re.compile(r"^run-tests\.sh$"),
    re.compile(r"^verify[-_].*\.(py|sh|js)$"),
    re.compile(r"^.*-test\.(js|py)$"),
)
SOURCE_TREES = ("tools", "services", "shell", "pwa", "scripts", "boot", "vm", "configs", "images")
SKIP_DIR_PARTS = ("__pycache__", "/fixtures", "/.build", "/.git", "/node_modules",
                  "/.venv", "/build/", "/dist/", "/security-fixtures")

# tree prefix -> owning build group (from the run-all-tests registry)
OWNERS = (
    ("tools/beta/workqueue", "bg-00-preflight"),
    ("tools/beta/regression-guard.sh", "bg-00-preflight"),
    ("tools/beta/tests/test_workqueue.py", "bg-00-preflight"),
    ("tools/beta/tests/test-regression-guard.sh", "bg-00-preflight"),
    ("tools/beta", "release"),
    ("tools/s10plus/a32", "bg-00-preflight"),
    ("tools/s10plus/a33/tests/hw-subsystems", "bg-08-hardware-subsystems"),
    ("tools/s10plus/a33/security-tests", "bg-05-security-permissions"),
    ("tools/s10plus/a33/snekbyte", "bg-07-specialty-apps"),
    ("tools/s10plus/a33", "bg-00-preflight+a33-groups"),
    ("tools/s10plus/a31", "bg-10-live-phone"),
    ("tools/s10plus", "legacy-per-cycle"),
    ("services/nuxel-portal", "bg-04-userspace-completion"),
    ("services/nuxel-notifications", "bg-04-userspace-completion"),
    ("services", "bg-04-userspace-completion"),
    ("shell/nuxel-shell/nuxel-permissions", "bg-05-security-permissions"),
    ("shell/nuxel-shell/nuxel-phone-data", "bg-06-core-phone-apps"),
    ("shell", "bg-06-core-phone-apps"),
    ("pwa/nuxel-apps/nuxtore", "bg-07-specialty-apps"),
    ("pwa/nuxel-apps", "bg-06-core-phone-apps"),
    ("pwa/nuxel-common", "bg-04-userspace-completion"),
    ("pwa/nuxel-home", "bg-02-boot-animation-launcher"),
    ("pwa", "bg-02-boot-animation-launcher"),
    ("scripts/nuxel-adb-flash-pack", "release"),
    ("scripts/s10plus-debug-pack", "bg-10-live-phone"),
    ("scripts", "release"),
    ("boot/s10plus", "bg-00-preflight"),
    ("boot", "release"),
    ("vm", "bg-11-vm-parity"),
    ("configs/nuxel", "bg-03-connectivity-time-audio-buttons"),
    ("configs", "release"),
    ("images/s10plus", "release"),
    ("images", "release"),
)


def owner_of(rel: str) -> str:
    for prefix, group in OWNERS:
        if rel == prefix or rel.startswith(prefix + "/"):
            return group
    return "unowned"


def is_test_file(name: str) -> bool:
    return any(p.match(name) for p in NAME_PATTERNS)


def discover(root: str):
    found = []
    for tree in SOURCE_TREES:
        base = os.path.join(root, tree)
        if not os.path.isdir(base):
            continue
        for dp, dn, fn in os.walk(base):
            if any(x in dp + "/" for x in SKIP_DIR_PARTS):
                continue
            for f in fn:
                if not is_test_file(f):
                    continue
                rel = os.path.relpath(os.path.join(dp, f), root)
                found.append(rel)
    return sorted(set(found))


def parse_registry(path: str):
    rows = []
    with open(path, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 8:
                continue
            rows.append(dict(zip(header, parts)))
    return rows


def commands(rows):
    return [(r["id"], r.get("cmd", "")) for r in rows]


def reachable(rel: str, cmds, root: str):
    """-> (bool, evidence-string)"""
    base = os.path.basename(rel)
    # 1. run directly
    for sid, cmd in cmds:
        if rel in cmd or base in cmd and os.path.dirname(rel) in cmd:
            return True, "run directly by %s" % sid
    # 2. a runner in this directory or up to three parents
    parts = rel.split("/")
    for depth in range(0, min(4, len(parts))):
        d = "/".join(parts[: len(parts) - 1 - depth]) if depth else "/".join(parts[:-1])
        for sid, cmd in cmds:
            for runner in ("run-tests.sh", "run-mock-tests.sh"):
                if ("%s/%s" % (d, runner)) in cmd:
                    return True, "run by runner %s/%s (%s)" % (d, runner, sid)
            m = re.search(r"(?:^|[\s/])(\S*run-[A-Za-z0-9_.-]*tests?\.sh)", cmd)
            if m and d and d in m.group(1):
                return True, "run by group runner %s (%s)" % (m.group(1), sid)
    # 3. a suite that walks a whole directory subtree, either by naming the
    #    directory or by a shell glob such as `find pwa -path "*/tests/*"`.
    parent = os.path.dirname(rel)
    for sid, cmd in cmds:
        if parent and parent in cmd and ("find" in cmd or "*.js" in cmd or "*.py" in cmd):
            return True, "globbed by %s" % sid
        for m in re.finditer(r"\*/?([A-Za-z0-9_.-]+)/\*", cmd):
            if ("/" + m.group(1) + "/") in ("/" + rel):
                return True, "globbed by %s (*/%s/* pattern)" % (sid, m.group(1))
    return False, ""


def main(argv=None):
    ap = argparse.ArgumentParser(description="test reachability audit for the release gate")
    ap.add_argument("--registry", required=True, help="suite-registry.tsv written by run-all-tests.sh")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__)) + "/../"))
    ap.add_argument("--json", nargs="?", const="-", default=None, help="write the audit as JSON")
    ap.add_argument("--strict-orphans", action="store_true",
                    help="treat every orphan as fatal (terminal integration mode)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isfile(args.registry):
        print("suite-coverage: registry not found: %s" % args.registry, file=sys.stderr)
        return 2
    rows = parse_registry(args.registry)
    cmds = commands(rows)
    tests = discover(root)

    covered, orphans = [], []
    for rel in tests:
        ok, why = reachable(rel, cmds, root)
        (covered if ok else orphans).append({"test": rel, "owner": owner_of(rel), "why": why})

    fatal = [o for o in orphans if args.strict_orphans or o["owner"] == "release"]
    warn = [o for o in orphans if o not in fatal]

    if not args.quiet:
        print("suite-coverage: discovered %d test artifacts, %d reachable from the gate, "
              "%d orphaned" % (len(tests), len(covered), len(orphans)))
        for o in covered:
            print("  covered  %-72s %-28s %s" % (o["test"], o["owner"], o["why"]))
        for o in warn:
            print("  ORPHAN   %-72s owner=%s (non-gating: group still in flight; "
                  "integration finding)" % (o["test"], o["owner"]))
        for o in fatal:
            print("  ORPHAN!  %-72s owner=%s (GATING)" % (o["test"], o["owner"]))

    if args.json:
        doc = {
            "schema_version": 1,
            "tool": "tools/beta/suite-coverage.py",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "registry": args.registry,
            "root": root,
            "strict_orphans": bool(args.strict_orphans),
            "counts": {"discovered": len(tests), "covered": len(covered),
                       "orphans": len(orphans), "gating_orphans": len(fatal)},
            "covered": covered,
            "orphans_non_gating": warn,
            "orphans_gating": fatal,
            "verdict": "FAIL" if fatal else "PASS",
        }
        out = json.dumps(doc, indent=2, sort_keys=True)
        if args.json == "-":
            print(out)
        else:
            with open(args.json, "w", encoding="utf-8") as fh:
                fh.write(out + "\n")

    if fatal:
        print("suite-coverage: FAIL — %d gating orphan(s)" % len(fatal), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
