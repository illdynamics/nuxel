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
  7. a phone unit is enabled into a USER target (`WantedBy=graphical-session.target`)
     => FAILED, while the VM-only camera portal is a recorded WARNING;
  8. the A26 containment script loses one of its four 4.14 repairs => FAILED;
  9. the single-owner live console (briq-04b rev 2) is enforced, not assumed: the
     builder ENABLING the provisioned-only `nuxel-console.service`, the unit
     losing its `ExecCondition`/`ConditionPathExists` guard, the unit switching to
     `Restart=always` (a second owner waiting to happen) and the unit being
     deleted altogether each => FAILED, while the baseline records the unit as
     installed-but-not-enabled in the report.
 10. the USER-manager units (shell/config/systemd-user/, VM/desktop surface) are
     validated under user-manager rules: a user unit that references a SYSTEM
     unit (`Wants=nuxel-web.service` - the defect both launcher units carried
     until rev 2) and a user unit enabled into a SYSTEM target each => FAILED.

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
    # the live console's device-side implementation, its single-owner guard and
    # the initramfs owner are cross-checked by the validator (section 3c), so a
    # faithful fixture must carry them.
    "tools/s10plus/a33/nuxel-console.c",
    "boot/initramfs/init.sh",
    "services/nuxel-console/bin/nuxel-console-free",
]


def make_fixture(dest: str) -> None:
    """Copy the unit set + the builder + the A26 script into <dest> verbatim."""
    rels = list(VSG.UNIT_SOURCES) + list(VSG.USER_UNIT_SOURCES) + PROVENANCE_UNITS + EXTRA_TREE_FILES
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
        check(report.get("unit_count", 0) >= 15,
              "baseline parses the full unit set (%d units)" % report.get("unit_count", 0))
        check(report.get("root") == os.path.abspath(base),
              "the report records which tree was validated (%s)" % report.get("root"))
        check(any("nuxel-camera-portal.service" in w and "graphical-session.target" in w
                  for w in report.get("warnings", [])),
              "the VM-only camera portal's no-op enablement is a recorded WARNING, not silence")
        check(report.get("vm_only_units") == ["nuxel-camera-portal.service"],
              "the report names the VM-only unit set explicitly (%s)" % report.get("vm_only_units"))
        check("nuxel-console.service" in (report.get("provisioned_not_enabled") or {}),
              "the report records the live console as installed-but-deliberately-not-enabled")
        check(not any("nuxel-console" in p for p in report.get("problems", [])),
              "the baseline raises no console-ownership problem (%s)"
              % [p for p in report.get("problems", []) if "console" in p][:1])
        check(report.get("builder_installed") and
              any("nuxel-console.service" == i for i in report["builder_installed"]),
              "the builder installs nuxel-console.service (%s)"
              % [i for i in (report.get("builder_installed") or []) if "console" in i])
        check(not any("console" in e for e in (report.get("builder_enabled") or [])),
              "the builder does NOT enable the console (%s)" % report.get("builder_enabled"))

        check(len(report.get("user_units") or {}) == 3,
              "the report validates the three VM/desktop user units (%s)"
              % sorted((report.get("user_units") or {}).keys()))
        check(not any("USER unit" in p or "user unit" in p for p in report.get("problems", [])),
              "the baseline user units raise no user-manager problem (%s)"
              % [p for p in report.get("problems", []) if "user unit" in p][:1])

        print("[service-graph] a USER unit that depends on a SYSTEM unit is fatal")
        mut = os.path.join(tmp, "user-refs-system")
        make_fixture(mut)
        upath = os.path.join(mut, "shell/config/systemd-user/nuxel-home-kiosk.service")
        utext = open(upath, errors="replace").read()
        check(not any(ln.strip().startswith("Wants=nuxel-web.service")
                      for ln in utext.splitlines()),
              "the launcher user unit no longer carries the system-unit dependency as an ACTIVE "
              "directive before mutation (the removal is documented in a comment)")
        insert_into_section(upath, "Unit", "Wants=nuxel-web.service")
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "names a SYSTEM unit from a USER unit"),
              "the cross-manager dependency is named: %s"
              % [p for p in report.get("problems", []) if "USER unit" in p][:1])

        print("[service-graph] a USER unit enabled into a SYSTEM target is fatal")
        mut = os.path.join(tmp, "user-system-target")
        make_fixture(mut)
        upath = os.path.join(mut, "shell/config/systemd-user/nuxel-phosh-agent.service")
        utext = open(upath, errors="replace").read()
        open(upath, "w").write(utext.replace("WantedBy=default.target",
                                             "WantedBy=multi-user.target"))
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "is a SYSTEM target in a USER unit"),
              "the wrong-scope enablement is named: %s"
              % [p for p in report.get("problems", []) if "USER unit" in p][:1])

        print("[service-graph] enabling the provisioned-only console is fatal (two owners)")
        mut = os.path.join(tmp, "console-enabled")
        make_fixture(mut)
        bpath = os.path.join(mut, "images/s10plus/build-phone-rootfs-inside-fedora.sh")
        btext = open(bpath, errors="replace").read()
        btext += ('ln -sf ../nuxel-console.service '
                  '"$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-console.service"\n')
        open(bpath, "w").write(btext)
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "provisioned-only"),
              "the two-owner enablement is named: %s"
              % [p for p in report.get("problems", []) if "console" in p][:1])

        print("[service-graph] a console unit that lost its single-owner guard is fatal")
        mut = os.path.join(tmp, "console-unguarded")
        make_fixture(mut)
        cpath = os.path.join(mut, "services/nuxel-console/systemd/nuxel-console.service")
        ctext = open(cpath, errors="replace").read()
        keep = [ln for ln in ctext.splitlines(keepends=True) if not ln.startswith("ExecCondition=")]
        check(len(keep) != len(ctext.splitlines(keepends=True)),
              "the ExecCondition line was located before mutation")
        open(cpath, "w").write("".join(keep))
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "ExecCondition"), "the lost port guard is named: %s"
              % [p for p in report.get("problems", []) if "console" in p][:1])

        print("[service-graph] a console unit that restarts into a second owner is fatal")
        mut = os.path.join(tmp, "console-restart")
        make_fixture(mut)
        cpath = os.path.join(mut, "services/nuxel-console/systemd/nuxel-console.service")
        ctext = open(cpath, errors="replace").read()
        open(cpath, "w").write(ctext.replace("Restart=no", "Restart=always"))
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "Restart=[") and has_problem(report, "restart loop"),
              "the restart loop is named: %s"
              % [p for p in report.get("problems", []) if "Restart" in p][:1])

        print("[service-graph] deleting the console unit is fatal (no debug path at all)")
        mut = os.path.join(tmp, "console-gone")
        make_fixture(mut)
        os.unlink(os.path.join(mut, "services/nuxel-console/systemd/nuxel-console.service"))
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "live console has no unit"),
              "the missing console declaration is named: %s"
              % [p for p in report.get("problems", []) if "console" in p][:1])

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

        print("[service-graph] a phone unit enabled into a USER target is fatal")
        mut = os.path.join(tmp, "usertarget")
        make_fixture(mut)
        unit = os.path.join(mut, "services/nuxel-web.service")
        text = open(unit, errors="replace").read()
        check("WantedBy=multi-user.target" in text,
              "nuxel-web.service is enabled into multi-user.target before mutation")
        open(unit, "w").write(text.replace("WantedBy=multi-user.target",
                                           "WantedBy=graphical-session.target"))
        rc, report = validate(mut)
        check(rc != 0, "verdict is FAILED (rc=%s)" % rc)
        check(has_problem(report, "is a USER target in a SYSTEM unit"),
              "the no-op enablement is named: %s"
              % [p for p in report.get("problems", []) if "USER target" in p][:1])

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
