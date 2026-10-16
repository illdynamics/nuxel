#!/usr/bin/env python3
"""Offline test for verify-service-graph.py (briq-04b).

The acceptance criterion for briq-04b is a service-graph validator that
"parses unit After/Requires/Wants, detect[s] cycles and unsatisfied deps" and
whose green run really means something.  A validator that has only ever been
run against the (already fixed) repository has never been *shown* to fail, so
this test mutates a faithful COPY of the tree and requires the validator to
report each defect class:

  1. `find_cycles()` detects a cycle in a synthetic graph, and finds none in a
     DAG (the detector is not a no-op);
  2. baseline: a verbatim copy of the repository's unit set validates green, so
     the fixture mechanism itself is faithful (no false failures);
  3. injected ordering cycle (`nuxel-bridge` ordered Before `nuxel-notifications`
     — the real A32 defect) => FAILED with "ordering cycle";
  4. injected unsatisfied dependency (`Requires=nuxel-dse-unit.service`) =>
     FAILED with "does not resolve";
  5. injected 4.14-forbidden dependency (`After=dbus-broker.service`) => FAILED
     with "forbidden on 4.14";
  6. builder installs a unit but does NOT enable it => FAILED (the boot graph is
     only reproducible if enablement is in the builder, not hot-patched);
  7. the A26 containment script loses one of its four 4.14 repairs => FAILED.

Every case runs against a temporary copy; the repository is never modified and
no device, partition or /Users/wicked/x/nuxel/.qq path is touched.

Usage: python3 tools/s10plus/a33/tests/test-service-graph.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
VERIFIER = os.path.join(ROOT, "tools", "s10plus", "a33", "verify-service-graph.py")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_service_graph", VERIFIER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


VSG = load_verifier()


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------
PROVENANCE_UNITS = [
    "tools/s10plus/a31/nuxel-wayland.service",
    "tools/s10plus/a31/nuxel-wl-fb.service",
    "tools/s10plus/a31/nuxel-touch-arm.service",
    "tools/s10plus/a31/seatd.service",
    "tools/s10plus/a32/nuxel-button-manager.service",
]
EXTRA_TREE_FILES = [
    "images/s10plus/build-phone-rootfs-inside-fedora.sh",
    "tools/s10plus/a26/nuxel-rootfs-fixes.sh",
]


def make_fixture(dest: str) -> None:
    """Copy the unit set + the builder + the A26 script into <dest> verbatim."""
    rels = list(VSG.UNIT_SOURCES) + PROVENANCE_UNITS + EXTRA_TREE_FILES
    for rel in rels:
        src = os.path.join(ROOT, rel)
        if not os.path.exists(src):
            raise SystemExit("fixture source missing: %s" % rel)
        dst = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def insert_into_section(path: str, section: str, line: str) -> None:
    """Insert `line` as the first line after the [section] header."""
    lines = open(path, errors="replace").read().splitlines(keepends=True)
    out, done = [], False
    for ln in lines:
        out.append(ln)
        if not done and ln.strip() == "[%s]" % section:
            out.append(line.rstrip("\n") + "\n")
            done = True
    if not done:
        raise SystemExit("section [%s] not found in %s" % (section, path))
    open(path, "w").write("".join(out))


def validate(root: str) -> tuple:
    """Run the validator in-process against `root`; return (rc, report)."""
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        rc = VSG.main(["--quiet", "--json", out], root=root)
        with open(out) as fh:
            report = json.load(fh)
    finally:
        os.unlink(out)
    return rc, report


def has_problem(report: dict, needle: str) -> bool:
    return any(needle in p for p in report.get("problems", []))


# ---------------------------------------------------------------------------
def main() -> int:
    print("[service-graph] the cycle detector is not a no-op")
    cyc = VSG.find_cycles({"a.service": {"b.service"}, "b.service": {"a.service"}})
    check(bool(cyc), "a 2-node cycle is detected (%s)" % (cyc or "none"))
    check(not VSG.find_cycles({"a.service": {"b.service"}, "b.service": {"c.service"}, "c.service": set()}),
          "a DAG produces no cycle")
    self_loop = VSG.find_cycles({"x.service": {"x.service"}})
    check(bool(self_loop), "a self-dependency is detected (%s)" % (self_loop or "none"))

    with tempfile.TemporaryDirectory() as tmp:
        print("[service-graph] baseline: a verbatim copy validates green")
        base = os.path.join(tmp, "base")
        make_fixture(base)
        rc, report = validate(base)
        check(rc == 0 and report["verdict"] == "OFFLINE_TESTED",
              "baseline fixture verdict=%s rc=%s problems=%s"
              % (report["verdict"], rc, report.get("problems")))
        check(report.get("unit_count", 0) >= 14,
              "baseline parses the full unit set (%d units)" % report.get("unit_count", 0))
        check(report.get("root") == os.path.abspath(base),
              "the report records which tree was validated (%s)" % report.get("root"))

        print("[service-graph] an injected ordering cycle is fatal")
        mut = os.path.join(tmp, "cycle")
        make_fixture(mut)
        insert_into_section(os.path.join(mut, "services/nuxel-bridge/systemd/nuxel-bridge.service"),
                            "Unit", "Before=nuxel-notifications.service")
        rc, report = validate(mut)
        check(rc != 0 and report["verdict"] == "FAILED", "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "ordering cycle"), "the cycle is named: %s"
              % [p for p in report.get("problems", []) if "cycle" in p][:1])

        print("[service-graph] an unsatisfied dependency is fatal")
        mut = os.path.join(tmp, "unsat")
        make_fixture(mut)
        insert_into_section(os.path.join(mut, "services/nuxel-web.service"),
                            "Unit", "Requires=nuxel-dse-unit.service")
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "does not resolve to any installed unit"),
              "the unsatisfied unit is named: %s"
              % [p for p in report.get("problems", []) if "resolve" in p][:1])

        print("[service-graph] a 4.14-forbidden dependency is fatal")
        mut = os.path.join(tmp, "forbidden")
        make_fixture(mut)
        insert_into_section(os.path.join(mut, "services/nuxel-session/systemd/nuxel-wayland.service"),
                            "Unit", "After=dbus-broker.service")
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "forbidden on 4.14"), "the 4.14 violation is named: %s"
              % [p for p in report.get("problems", []) if "forbidden" in p][:1])

        print("[service-graph] a unit the builder installs but never enables is fatal")
        mut = os.path.join(tmp, "noenable")
        make_fixture(mut)
        builder = os.path.join(mut, "images/s10plus/build-phone-rootfs-inside-fedora.sh")
        text = open(builder, errors="replace").read()
        needle = "nuxel-web.service           \"$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-web.service\""
        if needle not in text:
            # whitespace-insensitive fallback
            keep = [ln for ln in text.splitlines(keepends=True)
                    if not ("multi-user.target.wants/nuxel-web.service" in ln)]
            check(len(keep) != len(text.splitlines(keepends=True)),
                  "the builder's nuxel-web enablement line was located")
            text = "".join(keep)
        else:
            text = text.replace(needle + "\n", "")
        open(builder, "w").write(text)
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "nuxel-web.service") and
              any(("does not enable" in p or "builder enables" in p) for p in report.get("problems", [])),
              "the missing enablement is named: %s"
              % [p for p in report.get("problems", []) if "nuxel-web.service" in p][:1])

        print("[service-graph] a lost A26 4.14 repair is fatal")
        mut = os.path.join(tmp, "a26")
        make_fixture(mut)
        a26 = os.path.join(mut, "tools/s10plus/a26/nuxel-rootfs-fixes.sh")
        text = open(a26, errors="replace").read()
        check("dbus-daemon.service" in text, "the A26 script mentions dbus-daemon.service before mutation")
        open(a26, "w").write(text.replace("dbus-daemon.service", "dbus-daemon-mutated.service"))
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "A26 fix missing"), "the lost repair is named: %s"
              % [p for p in report.get("problems", []) if "A26" in p][:1])

    print("[service-graph] the repository itself is green")
    rc = VSG.main(["--quiet"])
    check(rc == 0, "the real tree validates OFFLINE_TESTED (rc=%s)" % rc)

    if FAILURES:
        print("\nFAILED: %d assertion(s)" % len(FAILURES))
        return 1
    print("\nAll service-graph validator checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
