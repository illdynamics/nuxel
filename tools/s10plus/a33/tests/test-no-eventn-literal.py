#!/usr/bin/env python3
"""Grep gate: no hard-coded /dev/input/event<N> node number anywhere in the A33
touch pipeline (mission invariant, briq-01a acceptance).

Every path in this pipeline must be discovered at runtime:
  * the tracer scans the input directory and selects BY CAPABILITY;
  * the shim scans the input directory and selects BY CAPABILITY;
  * the capture harness globs and re-uses the tracer's selection.

A literal node number is how the A23..A28 cycles kept measuring the wrong device,
so the gate is deliberately blunt: it rejects the literal in code, comments and
documents alike (use the placeholder form instead).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

# The literal must not appear as "/dev/input/event<digit>" nor as the bare
# "event<digit>" token in source files.
PATTERNS = [re.compile(r"/dev/input/event[0-9]"), re.compile(r"\bevent[0-9]+\b")]

TARGETS = [
    "tools/s10plus/a33/nuxel-touch-trace.py",
    "tools/s10plus/a33/nuxel-touch-capture.sh",
    "tools/s10plus/a33/nuxel-bootmode-guard.py",
    "tools/s10plus/a33/nuxel-libinput-path.c",
    "tools/s10plus/a31/nuxel-libinput-path.c",
    "tools/s10plus/a33/build-libinput-shim.sh",
    "tools/s10plus/a33/tests/test-touch-trace.py",
    "tools/s10plus/a33/tests/test-bootmode-guard.py",
    "tools/s10plus/a33/tests/test-capture-harness.py",
    "tools/s10plus/a33/tests/test-no-eventn-literal.py",
    "tools/s10plus/a33/tests/test-libinput-parity.py",
    "tools/s10plus/a33/tests/test-libinput-shim-invocation.py",
    "tools/s10plus/a33/tests/run-touch-tests.sh",
    "tools/s10plus/a33/touch-probe.html",
    "docs/beta-finalization/touch/PIPELINE-TRACE.md",
    "docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md",
    "docs/beta-finalization/manual-proof/01-touchscreen.md",
    "configs/libinput/nuxel-s10plus-touch.conf",
    "configs/libinput/README.md",
    "configs/nuxel/touch/bootmode-guard.json",
    "configs/nuxel/touch/README.md",
    "configs/nuxel/touch/nuxel-bootmode-guard.service",
    "configs/nuxel/touch/nuxel-bootmode-reboot.service",
    "tools/s10plus/a33/README.md",
    "tools/s10plus/a33/kernel-patches/README.md",
    "tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch",
    "docs/beta-finalization/touch/OFFLINE-TEST-RESULTS.md",
]
# Files that legitimately CONTAIN node names as *data under test* rather than as
# an assumption about the device.  They are not scanned for the bare token, and
# they are named here explicitly so the exclusion stays reviewable:
#   * tests/test-libinput-path-fixture.py — asserts the selector's OUTPUT, which
#     is by construction a node path; the selector it drives is scanned above;
#   * tests/fixtures/** — the synthetic sysfs trees themselves (event names ARE
#     the data under test).
DATA_UNDER_TEST = [
    "tools/s10plus/a33/tests/test-libinput-path-fixture.py",
    "tools/s10plus/a33/tests/fixtures/",
    # Archived LIVE captures under docs/beta-finalization/live/evidence/ (e.g.
    # touch-<ts>-*-live-run/evdev.txt) are raw DEVICE OUTPUT: node names there are
    # the data under test, not an assumption any tool makes.  They are not scanned,
    # and they are named here so the exclusion stays reviewable.
    "docs/beta-finalization/live/evidence/",
]

failures = 0
checked = 0
for rel in DATA_UNDER_TEST:
    print("NOTE %s: node names appear as data under test (excluded from the token rule)" % rel)
for rel in TARGETS:
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        print("SKIP absent %s (not created yet in this cycle)" % rel)
        continue
    checked += 1
    bad = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f, 1):
            for pat in PATTERNS:
                m = pat.search(line)
                if m:
                    bad.append("%s:%d: %s" % (rel, n, m.group(0)))
    if bad:
        failures += 1
        print("FAIL %s contains hard-coded node number(s):" % rel)
        for b in bad:
            print("     %s" % b)
    else:
        print("PASS %s: no hard-coded node number" % rel)

print("== grep gate: %d file(s) checked, %d failing ==" % (checked, failures))
sys.exit(1 if failures else 0)
