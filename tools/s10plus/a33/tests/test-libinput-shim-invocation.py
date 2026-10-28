#!/usr/bin/env python3
"""briq-01b: the shim is only useful if the REAL invocation still preloads it.

The A31/A32 baseline deploys the interposer as
`LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so` on the `nuxel-wayland`
service.  A hardened shim that nothing preloads is dead code, and a shim preloaded
with a different environment (no headless+libinput backend, no seat backend) would
be validated by tests that exercise a configuration the phone does not run.

This test pins the invocation chain, source -> build -> unit -> state file -> the
path the tracer reads, so bg-02/bg-10 parity work can verify it mechanically:

  tools/s10plus/a31|a32/build-*.sh   build libnuxel-libinput-path.so
  services/nuxel-session/systemd/nuxel-wayland.service
                                     Environment=LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so
  /run/nuxel-libinput-path.state     what the shim logs, and what the tracer grades

No phone, no /dev/input, no libinput: it is a source/unit consistency gate.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

SERVICE = os.path.join(ROOT, "services", "nuxel-session", "systemd", "nuxel-wayland.service")
A32_SERVICE = os.path.join(ROOT, "tools", "s10plus", "a32", "nuxel-wayland.service")
A31_BUILD = os.path.join(ROOT, "tools", "s10plus", "a31", "build-a31.sh")
A32_BUILD = os.path.join(ROOT, "tools", "s10plus", "a32", "build-a32.sh")
BUILD = os.path.join(A33, "build-libinput-shim.sh")
SRC = os.path.join(A33, "nuxel-libinput-path.c")
TRACER = os.path.join(A33, "nuxel-touch-trace.py")

failures = []


def check(cond, what, extra=""):
    if cond:
        print("PASS %s" % what)
    else:
        print("FAIL %s%s" % (what, (" :: " + extra) if extra else ""))
        failures.append(what)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


print("== the LD_PRELOAD invocation the A32 baseline uses ==")
svc = read(SERVICE)
check("LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so" in svc,
      "nuxel-wayland.service preloads the shim from /usr/lib/nuxel/", SERVICE)
check(re.search(r"^Environment=LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path\.so$",
                svc, re.M) is not None,
      "it is an Environment= line (systemd, not a shell export)")
check("WLR_BACKENDS=headless,libinput" in svc,
      "the compositor is started with the libinput backend (the shim's entry points)")
check("LIBSEAT_BACKEND=" in svc,
      "a seat backend is set (the shim keeps the libseat path for device opens)")
check("WLR_LIBINPUT_NO_DEVICES=1" in svc,
      "wlroots is told zero devices is survivable (charger-mode boot keeps phoc up)")
check("nuxel-libinput-path.state" in read(SRC),
      "the shim logs to /run/nuxel-libinput-path.state, the file the tracer grades")
check("/run/nuxel-libinput-path.state" in read(TRACER),
      "the tracer reads the same state path (one contract, two implementations)")

print("== the build chain that produces the preloaded object ==")
for p, what in ((A31_BUILD, "A31"), (A32_BUILD, "A32")):
    t = read(p)
    check("libnuxel-libinput-path.so" in t, "%s build produces libnuxel-libinput-path.so" % what)
    check("-shared" in t and "-fPIC" in t, "%s builds a shared PIC object (an interposer)" % what)
t = read(BUILD)
check("libnuxel-libinput-path.so" in t and "-shared" in t and "-fPIC" in t,
      "the A33 build produces the same shared PIC object", BUILD)
check("-O2" in t and "-Wall" in t and "-std=gnu11" in t,
      "the A33 build flags are explicit and deterministic (no -march=native, no -Ofast)")
check("-march=native" not in t and "-Ofast" not in t and "-ffast-math" not in t,
      "no host-specific optimisation leaks into the aarch64 object")
check("-DNUXEL_SHIM_SELFTEST" in t,
      "the same source builds the host selftest binary the offline tests drive")

print("== one implementation, two names (parity) ==")
a33 = read(SRC)
a31 = read(os.path.join(ROOT, "tools", "s10plus", "a31", "nuxel-libinput-path.c"))
check(bool(a33) and a33 == a31,
      "the A33 source and the A31 (deployed) source are byte-identical")
for sym in ("libinput_udev_create_context", "libinput_udev_assign_seat", "libinput_dispatch",
            "libseat_open_device", "libinput_path_add_device"):
    check(sym in a33, "the shim still interposes %s" % sym)

print("== single-client discipline (never two opens against one node) ==")
check("ignored=already-tracked" in a33 or "already-tracked" in a33,
      "a repeated add of the same node is ignored (dedup by device name)")
check("tracked_add" in a33 and "MAX_TRACKED" in a33,
      "the tracked-device table is bounded, so a device storm cannot grow it")
check("TRACKED_TABLE_FULL" in a33,
      "a full table is logged instead of silently dropping or re-opening devices")
check("by-path" in a33,
      "a stable /dev/input/by-path devlink is recorded for the accepted node")
check("ZERO_DEVICES" in a33,
      "device absence is logged as ZERO_DEVICES (fails closed, never invents a device)")

print("== the deployed object's recorded hash is still the one this source builds ==")
dep = read(os.path.join(ROOT, "docs", "s10plus-autonomous-boot-repair", "BETA-FINALIZER",
                        "09-LIVE-DEPLOYMENTS.md"))
m = re.search(r"libnuxel-libinput-path\.so`?\s*\|\s*`?([0-9a-f]{64})", dep)
check(m is not None, "the live-deployment record carries the deployed .so SHA-256", dep[:0])
if m:
    print("INFO deployed libnuxel-libinput-path.so sha256 = %s" % m.group(1))
    print("INFO (rollback: restore that hash; the source behind it is tools/s10plus/a31/nuxel-libinput-path.c)")

print("== %d failing check(s) ==" % len(failures))
sys.exit(1 if failures else 0)
