#!/usr/bin/env python3
"""Offline tests for the capability-based libinput shim (A33 / briq-01b).

Runs the SAME decision code that ships in libnuxel-libinput-path.so, compiled for
this host (-DNUXEL_SHIM_SELFTEST), against the synthetic sysfs/uevent fixtures in
tools/s10plus/a33/tests/fixtures/.  No phone, no /dev/input, no libinput.

What is asserted (the briq's acceptance):
  * a DIRECT multitouch panel is SELECTED, and it is selected by capability;
  * a non-DIRECT device is REJECTED with the INPUT_PROP_DIRECT reason;
  * node numbers sort NUMERICALLY (event2 before event10, never lexical);
  * a DIRECT+ABS_MT device with a degenerate range is REJECTED;
  * device absence -> ZERO_DEVICES and exit status 0 (the compositor survives);
  * hotplug: add / duplicate-add / remove / remove-again / re-appearance are
    all tracked correctly and always exit 0.

The inotify *watcher thread* itself only exists in the deployed .so (Linux), so it
cannot run here; what it feeds (the bounded queue + shim_apply decision) is exactly
what --hotplug drives.  That boundary is stated here on purpose - this test does
not claim to have measured the phone.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
FIX = os.path.join(HERE, "fixtures")
SELFTEST = os.path.join(ROOT, "build", "out", "s10plus", "a33", "nuxel-libinput-path-selftest")

failures = []


def check(cond, what, extra=""):
    if cond:
        print("PASS %s" % what)
    else:
        print("FAIL %s%s" % (what, (" :: " + extra) if extra else ""))
        failures.append(what)


def run(args):
    p = subprocess.run([SELFTEST] + args, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


def selected(out):
    return [l.split()[1] for l in out.splitlines() if l.startswith("SELECTED ")]


def main():
    if not os.path.isfile(SELFTEST):
        print("FAIL selftest binary absent (%s)\n     build it: tools/s10plus/a33/build-libinput-shim.sh --selftest" % SELFTEST)
        return 1
    print("== libinput-path capability fixtures (%s) ==" % os.path.basename(SELFTEST))

    # 1. the real case: gpio_keys rejected, sec_touchscreen selected
    rc, out, err = run(["--scan", os.path.join(FIX, "sec-ts-only")])
    check(rc == 0, "sec-ts-only: exit 0", "rc=%d err=%s" % (rc, err.strip()[:200]))
    check(selected(out) == ["/dev/input/event2"], "sec-ts-only: exactly the DIRECT panel is selected", out)
    check(any("gpio_keys" in l and "INPUT_PROP_DIRECT absent" in l for l in out.splitlines()),
          "sec-ts-only: gpio_keys rejected with the INPUT_PROP_DIRECT reason", out)
    check(any(l.startswith("SCAN_RESULT nodes=2 accepted=1") for l in out.splitlines()),
          "sec-ts-only: 2 nodes seen, 1 accepted", out)

    # 2. capability, not node number: swap the roles and the answer follows the property
    rc, out, err = run(["--scan", os.path.join(FIX, "degenerate-range")])
    check(rc == 0, "degenerate-range: exit 0", err.strip()[:200])
    check(selected(out) == [], "degenerate-range: nothing selected", out)
    check(any("degenerate axis range x=100..100" in l for l in out.splitlines()),
          "degenerate-range: the degenerate ABS_MT range is the stated reason", out)

    # 3. numeric ordering
    rc, out, err = run(["--scan", os.path.join(FIX, "numeric-order")])
    check(selected(out) == ["/dev/input/event2", "/dev/input/event10"],
          "numeric-order: event2 sorts before event10", out)

    # 4. absence (charger-mode boot: no panel node at all) must never fail
    rc, out, err = run(["--scan", os.path.join(FIX, "empty")])
    check(rc == 0, "empty: exit 0 on ZERO_DEVICES", "rc=%d" % rc)
    check("ZERO_DEVICES" in out, "empty: ZERO_DEVICES is reported", out)
    check(any(l.startswith("SCAN_RESULT nodes=0 accepted=0") for l in out.splitlines()),
          "empty: 0 nodes, 0 accepted", out)
    rc, out, err = run(["--scan", "/nonexistent-fixture-root"])
    check(rc == 0 and "ZERO_DEVICES" in out, "missing root: no crash, ZERO_DEVICES, exit 0", out + err)

    # 5. hotplug bookkeeping (the logic the inotify watcher feeds)
    ops = os.path.join(HERE, "fixtures", "hotplug-ops.txt")
    with open(ops, "w") as f:
        f.write("# add / duplicate add / remove / remove again / re-appearance / unknown node\n"
                "add event3\nadd event3\ndrain\nremove event3\nremove event3\n"
                "add event3\nadd event9\nremove event9\n")
    rc, out, err = run(["--hotplug", os.path.join(FIX, "hotplug"), ops])
    check(rc == 0, "hotplug: exit 0", err.strip()[:200])
    check("HOTPLUG ADD event3 ACCEPT tracked=1" in out, "hotplug: first add tracks the panel", out)
    check("HOTPLUG ADD event3 IGNORED already-tracked" in out, "hotplug: duplicate add is ignored", out)
    check("HOTPLUG REMOVE event3 REMOVED tracked=0" in out, "hotplug: remove un-tracks the panel", out)
    check("HOTPLUG REMOVE event3 NOT_TRACKED" in out, "hotplug: second remove is ignored (absence is safe)", out)
    check("HOTPLUG ADD event9 REJECT reason=metadata-or-open-failed" in out,
          "hotplug: a node that cannot be probed is rejected, not tracked", out)
    check("TRACKED final=1" in out, "hotplug: re-appearance leaves exactly one tracked device", out)
    os.unlink(ops)

    print("== %d failing assertion(s) ==" % len(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
