#!/usr/bin/env python3
"""Offline tests for the charger/LPM boot-mode guard (briq-01c).

Everything here runs WITHOUT a phone: the classifier is driven by the synthetic
captures in tests/fixtures/bootmode/, and the reboot gate is driven through the
pure ``reboot_decision()`` function so every suppression branch is exercised
exactly.  No reboot is ever executed: the fixture mode refuses to run the reboot
command, and the print-only mode is asserted to have executed nothing.

What is asserted:
  * a charger-mode capture is classified CHARGER/LPM and reports touch DISABLED;
  * the four independent markers (androidboot.mode=charger, lpcharge=1 on a real
    cmdline, sec_bat_is_lpm_check: 1, sec_ts_init -ENODEV) are each recognised;
  * a *prose* document that merely mentions lpcharge=1 is NOT graded as device
    evidence (the anti-fabrication rule) - it lands in UNKNOWN, never in LPM;
  * a normal boot is classified NORMAL and expects the touch driver;
  * the permanent-fix verdict is BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED /
    NOT_DEPLOYED (never claimed as fixed);
  * the reboot gate refuses: no --reboot; no acknowledgement; allow_reboot=false;
    an owner-test lock; an active cooldown; uptime below the floor; unknown
    charger state - and permits only when every gate passes;
  * fixture mode never executes a reboot command.
"""
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GUARD = os.path.join(A33, "nuxel-bootmode-guard.py")
FIX = os.path.join(HERE, "fixtures", "bootmode")
CFG_ALLOW = os.path.join(FIX, "configs", "allow-reboot.json")
CFG_DENY = os.path.join(FIX, "configs", "deny-reboot.json")

failures = []


def check(cond, what, extra=""):
    if cond:
        print("PASS %s" % what)
    else:
        print("FAIL %s%s" % (what, (" :: " + extra) if extra else ""))
        failures.append(what)


def run(args, timeout=90):
    p = subprocess.run([sys.executable, GUARD] + args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def load_guard():
    spec = importlib.util.spec_from_file_location("nuxel_bootmode_guard", GUARD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def base_args(fixture):
    return ["--offline-fixture", os.path.join(FIX, fixture), "--no-write",
            "--ignore-locks", "--ignore-cooldown"]


def main():
    print("== bootmode guard: boot classification ==")
    rc, out = run(base_args("lpm-boot"))
    check(rc == 10, "charger-mode capture -> exit 10 (LPM detected, no action)", "rc=%d" % rc)
    check("BOOTMODE=CHARGER_LPM" in out, "LPM capture classified CHARGER_LPM", out[-400:])
    check("TOUCH_AVAILABLE=false" in out, "LPM: touch reported DISABLED", out[-400:])
    check("androidboot.mode=charger" in out, "androidboot.mode=charger is the cited evidence")
    check("lpcharge=1" in out, "lpcharge=1 is the cited evidence")
    check("Low power charging mode: 1" in out, "sec_bat_is_lpm_check marker is cited")
    check("Do not load driver due to" in out, "sec_ts_init -ENODEV marker is cited")
    check("PERMANENT_FIX=BLOCKED_KERNEL BOOT_UPDATE_REQUIRED NOT_DEPLOYED" in out,
          "permanent fix is honestly marked BLOCKED_KERNEL / NOT_DEPLOYED")
    check("unplug" in out.lower(), "owner-readable message says to unplug + reboot normally")

    rc, out = run(base_args("normal-boot"))
    check(rc == 0, "normal capture -> exit 0", "rc=%d" % rc)
    check("BOOTMODE=NORMAL" in out, "normal capture classified NORMAL")
    check("SEC_TOUCHSCREEN_REGISTERED=1" in out, "normal capture: driver registration seen")
    check("TOUCH_AVAILABLE=true" in out, "normal capture: touch reported available")

    rc, out = run(base_args("prose-mention"))
    check("BOOTMODE=CHARGER_LPM" not in out,
          "a prose note mentioning lpcharge=1 is NOT graded as a charger-mode boot")
    check("BOOTMODE=UNKNOWN" in out, "prose-only capture lands in UNKNOWN")
    check(rc == 2, "UNKNOWN is an error-ish exit (absence of evidence is not a pass)", "rc=%d" % rc)

    print("== bootmode guard: the reboot gate (pure decision) ==")
    g = load_guard()
    cfg = dict(g.DEFAULT_CONFIG)
    cfg["allow_reboot"] = True
    locks = []
    # 1. not requested
    d = g.reboot_decision(cfg, "charger-lpm", False, False, True, uptime=999, locks=[], cooldown=0, charger=True)
    check(d["reboot"] is False and "no --reboot" in d["reason"], "gate: nothing happens without --reboot")
    # 2. acknowledgement missing
    d = g.reboot_decision(cfg, "charger-lpm", False, True, False, uptime=999, locks=[], cooldown=0, charger=True)
    check(d["reboot"] is False and "i-understand" in d["reason"], "gate: --reboot needs the acknowledgement")
    # 3. config denies
    deny = dict(cfg); deny["allow_reboot"] = False
    d = g.reboot_decision(deny, "charger-lpm", False, True, True, uptime=999, locks=[], cooldown=0, charger=True)
    check(d["reboot"] is False and "allow_reboot" in d["reason"], "gate: config allow_reboot=false blocks")
    # 4. owner-test lock
    d = g.reboot_decision(cfg, "charger-lpm", False, True, True, uptime=999,
                          locks=["/run/nuxel-touch-capture.lock"], cooldown=0, charger=True)
    check(d["reboot"] is False and "lock present" in d["reason"], "gate: an owner-test lock suppresses")
    # 5. cooldown
    d = g.reboot_decision(cfg, "charger-lpm", False, True, True, uptime=999, locks=[], cooldown=120, charger=True)
    check(d["reboot"] is False and "cooldown" in d["reason"], "gate: cooldown suppresses (no blind repeat reboots)")
    # 6. uptime floor
    d = g.reboot_decision(cfg, "charger-lpm", False, True, True, uptime=5, locks=[], cooldown=0, charger=True)
    check(d["reboot"] is False and "uptime" in d["reason"], "gate: uptime floor suppresses")
    # 7. charger unknown
    d = g.reboot_decision(cfg, "charger-lpm", False, True, True, uptime=999, locks=[], cooldown=0, charger=None)
    check(d["reboot"] is False and "charger state is unknown" in d["reason"],
          "gate: unknown charger state suppresses (never reboot a device about to lose power)")
    # 8. all gates pass
    d = g.reboot_decision(cfg, "charger-lpm", False, True, True, uptime=999, locks=[], cooldown=0, charger=True)
    check(d["reboot"] is True, "gate: reboot permitted only when every gate passes")
    # 9. a normal boot is never rebooted
    d = g.reboot_decision(cfg, "normal", False, True, True, uptime=999, locks=[], cooldown=0, charger=True)
    check(d["reboot"] is False, "gate: a normal boot is never rebooted by this tool")

    print("== bootmode guard: execution safety ==")
    rc, out = run(base_args("lpm-boot") + ["--reboot", "--i-understand-this-reboots-the-phone",
                                           "--print-only", "--assume-charger",
                                           "--fake-uptime", "999", "--config", CFG_ALLOW])
    check(rc == 13, "print-only: decision reached, nothing executed (exit 13)", "rc=%d\n%s" % (rc, out[-500:]))
    check("WOULD_RUN=systemctl reboot" in out, "print-only prints the exact reboot command")
    check("nothing was executed" in out, "print-only states that nothing was executed")
    check("REBOOT_ACTION" not in out or "issued" not in out, "print-only never reports an issued reboot")

    rc, out = run(base_args("lpm-boot") + ["--reboot", "--i-understand-this-reboots-the-phone",
                                           "--print-only", "--assume-charger",
                                           "--fake-uptime", "999", "--config", CFG_DENY])
    check(rc == 12, "deny config: reboot suppressed (exit 12)", "rc=%d\n%s" % (rc, out[-400:]))
    check("suppressed" in out, "deny config: suppression is stated with a reason")

    rc, out = run(base_args("lpm-boot") + ["--reboot", "--i-understand-this-reboots-the-phone",
                                           "--assume-charger", "--fake-uptime", "999", "--config", CFG_ALLOW])
    check("FIXTURE MODE" in out or "print-only" in out or rc in (11, 13),
          "fixture mode either refuses to execute or reports print-only", "rc=%d\n%s" % (rc, out[-400:]))
    check("REBOOT_EXEC" not in out, "fixture mode never executes a reboot command")

    print("== %d failing assertion(s) ==" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
