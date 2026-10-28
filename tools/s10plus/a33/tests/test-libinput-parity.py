#!/usr/bin/env python3
"""One implementation, one gate: the deployed A31 copy of the shim must stay
byte-identical to the authoritative A33 source.

tools/s10plus/a31/build-a31.sh compiles tools/s10plus/a31/nuxel-libinput-path.c;
the hardened implementation (capability selection, hotplug recovery, udev-DB
seeding) lives at tools/s10plus/a33/nuxel-libinput-path.c.  Two files that are
supposed to be the same code must be provably the same code, otherwise the
offline tests validate something else than what is deployed.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
A33 = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-libinput-path.c")
A31 = os.path.join(ROOT, "tools", "s10plus", "a31", "nuxel-libinput-path.c")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


failures = 0
for p in (A33, A31):
    if not os.path.isfile(p):
        print("FAIL missing %s" % p)
        failures += 1
if not failures:
    a, b = sha(A33), sha(A31)
    print("a33 sha256 %s" % a)
    print("a31 sha256 %s" % b)
    if a == b:
        print("PASS the deployed A31 copy is byte-identical to the A33 source")
    else:
        print("FAIL the deployed A31 copy has drifted from the A33 source")
        print("     fix: cp tools/s10plus/a33/nuxel-libinput-path.c tools/s10plus/a31/nuxel-libinput-path.c")
        failures += 1
    # the shim must still be an interposer, not an ordinary library
    with open(A33) as f:
        src = f.read()
    for sym in ("libinput_udev_create_context", "libinput_udev_assign_seat",
                "libinput_dispatch", "libseat_open_device", "NUXEL_INPUT_PROP_DIRECT"):
        if sym in src:
            print("PASS shim source still references %s" % sym)
        else:
            print("FAIL shim source lost %s" % sym)
            failures += 1
print("== parity: %d failing check(s) ==" % failures)
sys.exit(1 if failures else 0)
