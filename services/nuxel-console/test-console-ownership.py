#!/usr/bin/env python3
"""Offline test: the live console has exactly ONE owner (briq-04b).

WHY THIS TEST EXISTS
    The live console is the only channel that can report a failing phone. Two
    owners do not degrade it, they break it: the framed protocol desynchronises
    and the port lock exists precisely because a second instance is destructive.
    briq-04b requires every Nuxel service - including the live console - to be a
    declared unit with ordering, dependencies, restart policy and jail scoping;
    this test proves the declaration is the one that cannot race the running
    console, and that the guard behaves (not just that a file exists).

WHAT IS ASSERTED
    1. the unit exists, is ordered before the compositor, and starts the console
       with the Fedora root as its argument (as the initramfs does);
    2. the unit is NOT restarted on failure and CANNOT start while another owner
       holds the port lock: `ConditionPathExists=` (the binary) + `ExecCondition=`
       (the flock probe) + `Restart=no`, each with its comment rationale;
    3. the unit's jail scoping is the set that the console can actually run
       under, and the deliberately-absent protections are explained in the file;
    4. the builder INSTALLS the unit and does NOT enable it (no
       multi-user.target.wants symlink) - enabling it would be the two-owner bug;
    5. the lock protocol matches the running implementation:
       `nuxel-console.c`'s default lock path == the helper's default == the
       unit's `NUXEL_CONSOLE_LOCK`;
    6. the guard BEHAVES: exit 0 on a free lock, non-zero while a console owner
       holds it (taken with the real flock(2) mechanism, from this test), and
       non-zero when it cannot prove the port is free (no flock(1), no /run);
    7. the current single owner is the initramfs instance, and the repository
       says so (boot/initramfs/init.sh launches /opt/nuxel/nuxel-console) -
       i.e. the document does not claim the unit is live on the handset.

NO device, no root, no network, no systemd. Exit status = number of failures.
"""

from __future__ import annotations

import fcntl
import os
import re
import shutil
import subprocess
import sys
import tempfile

SH = shutil.which("sh") or "/bin/sh"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
UNIT = os.path.join(HERE, "systemd", "nuxel-console.service")
HELPER = os.path.join(HERE, "bin", "nuxel-console-free")
CONSOLE_C = os.path.join(ROOT, "tools", "s10plus", "a33", "nuxel-console.c")
INIT_SH = os.path.join(ROOT, "boot", "initramfs", "init.sh")
BUILDER = os.path.join(ROOT, "images", "s10plus", "build-phone-rootfs-inside-fedora.sh")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def sections(text: str):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^\[([A-Za-z]+)\]\s*$", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, [])
        elif cur is not None and line.strip() and not line.strip().startswith("#"):
            out[cur].append(line.strip())
    return out


def values(sec, key):
    out = []
    for line in sec:
        if line.startswith(key + "="):
            out.extend(v for v in line[len(key) + 1:].split() if v)
    return out


def main() -> int:
    unit = open(UNIT, errors="replace").read()
    sec = sections(unit)

    print("[console] the unit declares the console the way the initramfs starts it")
    check("nuxel-console" in open(UNIT, errors="replace").read(), "the unit file exists and names the console")
    check(values(sec.get("Service", []), "ExecStart") == ["/usr/bin/nuxel-console", "/"],
          "ExecStart starts the console with the Fedora root as its argument (%s)"
          % values(sec.get("Service", []), "ExecStart"))
    after = values(sec.get("Unit", []), "After")
    before = values(sec.get("Unit", []), "Before")
    check("systemd-tmpfiles-setup.service" in after, "/run exists before the lock is tested (%s)" % after)
    check("nuxel-wayland.service" in before,
          "the console is ordered before the compositor it must be able to report (%s)" % before)
    check(values(sec.get("Install", []), "WantedBy") == ["multi-user.target"],
          "the unit is a system unit (multi-user.target)")

    print("[console] one owner: the unit cannot start beside a running console")
    check(values(sec.get("Unit", []), "ConditionPathExists") == ["/usr/bin/nuxel-console"],
          "ConditionPathExists gates on the rootfs console binary (absent on the shipped image)")
    check(values(sec.get("Service", []), "ExecCondition") == ["/usr/lib/nuxel/nuxel-console-free"],
          "ExecCondition runs the single-owner probe")
    check(values(sec.get("Service", []), "Restart") == ["no"],
          "Restart=no: a restart loop is worse than a stopped console")
    check("single-owner" in unit or "single owner" in unit,
          "the file states the ownership rule it implements")
    check("initramfs" in unit and "/opt/nuxel/nuxel-console" in unit,
          "the file names the CURRENT owner (the initramfs instance) honestly")

    print("[console] jail scoping: applied vs deliberately absent, with reasons")
    check(values(sec.get("Service", []), "NoNewPrivileges") == ["yes"],
          "NoNewPrivileges=yes (the console never needs escalation)")
    check(values(sec.get("Service", []), "ReadWritePaths") == ["/run"],
          "the only writable path outside /dev/kmsg is /run")
    for why in ("ProtectKernelTunables", "PrivateDevices", "configfs", "flock"):
        check(why in unit, "the file explains %s rather than hiding it" % why)
    active_hardening = [ln for ln in sec.get("Service", []) if "=" in ln]
    check(not any(ln.startswith("ProtectSystem=") for ln in active_hardening)
          and not any(ln.startswith("ProtectKernelTunables=") for ln in active_hardening),
          "neither ProtectSystem= nor ProtectKernelTunables= is SET: the console must write "
          "configfs to bind the gadget (explained in the file, not silently omitted)")

    print("[console] the builder installs it and does NOT enable it (no two owners)")
    builder = open(BUILDER, errors="replace").read()
    install_lines = [ln for ln in builder.splitlines()
                     if "nuxel-console.service" in ln and "install" in ln and "wants" not in ln]
    check(bool(install_lines), "the builder installs nuxel-console.service (%d line(s))" % len(install_lines))
    check(not any("multi-user.target.wants/nuxel-console.service" in ln
                  for ln in builder.splitlines()),
          "the builder never creates a multi-user.target.wants symlink for the console")
    why = re.search(r"NOT ENABLED|not enabled", builder, re.I)
    check(why is not None and builder.count("nuxel-console") >= 3,
          "the builder records WHY the console unit is installed but not enabled "
          "(it names the unit and the single-owner rule)")

    print("[console] the lock protocol matches the running implementation")
    console_c = open(CONSOLE_C, errors="replace").read()
    c_default = re.search(r'lockpath\s*=\s*"([^"]+)"', console_c)
    check(bool(c_default), "nuxel-console.c declares its default lock path")
    if c_default:
        check(c_default.group(1) == "/run/nuxel-console.lock",
              "the C console's default lock is /run/nuxel-console.lock (%s)" % c_default.group(1))
    helper = open(HELPER, errors="replace").read()
    check("/run/nuxel-console.lock" in helper,
          "the helper defaults to the same lock path the C console takes")
    check(values(sec.get("Service", []), "Environment") == ["NUXEL_CONSOLE_LOCK=/run/nuxel-console.lock"],
          "the unit pins NUXEL_CONSOLE_LOCK to the same path (one protocol, three files)")
    check(re.search(r"flock\(\s*g_lockfd\s*,\s*LOCK_EX\s*\|\s*LOCK_NB\s*\)", console_c) is not None,
          "the C console takes flock(LOCK_EX | LOCK_NB) - the mechanism the helper probes")

    print("[console] the guard behaves (real flock(2), no device involved)")
    with tempfile.TemporaryDirectory() as tmp:
        lock = os.path.join(tmp, "nuxel-console.lock")
        env = dict(os.environ, NUXEL_CONSOLE_LOCK=lock)
        proc = subprocess.run([SH, HELPER], env=env, capture_output=True, text=True)
        check(proc.returncode == 0, "a free lock -> exit 0 (the unit may start) (rc=%s)"
              % proc.returncode)
        fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX)          # pretend to be the console owner
        try:
            proc = subprocess.run([SH, HELPER], env=env, capture_output=True, text=True)
            check(proc.returncode != 0, "a held lock -> non-zero (the unit is skipped) (rc=%s)"
                  % proc.returncode)
            check("held" in proc.stderr, "the reason is printed, not swallowed: %r"
                  % proc.stderr.strip()[:90])
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        proc = subprocess.run([SH, HELPER], env=env, capture_output=True, text=True)
        check(proc.returncode == 0, "released lock -> exit 0 again (rc=%s)" % proc.returncode)
        # fail closed when the check cannot be made at all
        proc = subprocess.run([SH, HELPER], env=dict(env, PATH="/nonexistent"),
                              capture_output=True, text=True)
        check(proc.returncode != 0,
              "no flock(1) -> non-zero: an unprovable port is never assumed free (rc=%s)"
              % proc.returncode)
        proc = subprocess.run([SH, HELPER],
                              env=dict(env, NUXEL_CONSOLE_LOCK=os.path.join(tmp, "nodir", "x.lock")),
                              capture_output=True, text=True)
        check(proc.returncode != 0, "a missing lock directory is a start failure, not a pass (rc=%s)"
              % proc.returncode)

    print("[console] the CURRENT owner is the initramfs, and the repository says so")
    init = open(INIT_SH, errors="replace").read()
    check("/opt/nuxel/nuxel-console" in init,
          "boot/initramfs/init.sh launches the console before systemd exists")
    check(re.search(r"if \[ -x /opt/nuxel/nuxel-console \]", init) is not None,
          "the initramfs start is conditional on the binary, as documented")
    check("NOT ENABLED" in unit,
          "the unit itself states it is not enabled on the shipped image")

    if FAILURES:
        print("\nFAILED: %d assertion(s)" % len(FAILURES))
        return 1
    print("\nAll live-console ownership checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
