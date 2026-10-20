#!/usr/bin/env python3
"""Triage a Nuxel ram-console record (/proc/last_kmsg) from TWRP.

Segments the ring buffer into boot sessions, identifies the Nuxel session(s) by
the Nuxel kernel banner / initramfs markers, and reports the A16/A17 decision
points with counts. Read-only; prints raw line numbers so any claim can be
checked against the log.

usage: 20-triage-nuxel-boot.py <last_kmsg> [--session N] [--grep PATTERN]
"""
import argparse
import re
import sys

BANNER = re.compile(r"Linux version (\S+).*?#(\d+) SMP PREEMPT (.+?) UTC (\d{4})")
SB = re.compile(r"Samsung S-Boot 4\.0")
START = re.compile(r"Starting kernel\.\.\.")
REC = re.compile(r"recovery: Loading entire partition")


def load(path):
    with open(path, "rb") as fh:
        data = fh.read()
    data = data.replace(b"\x00", b"")
    return data.decode("utf-8", "replace").split("\n")


def segments(lines):
    """Return [(start_line, end_line, kind)] for each S-Boot..next S-Boot span."""
    starts = [i for i, l in enumerate(lines) if SB.search(l)]
    segs = []
    for n, s in enumerate(starts):
        e = starts[n + 1] - 1 if n + 1 < len(starts) else len(lines) - 1
        kind = "recovery/twrp" if any(REC.search(lines[i]) for i in range(s, min(s + 200, e))) else "kernel-boot"
        segs.append((s, e, kind))
    return segs


def nuxel_boot_sessions(lines, segs):
    out = []
    for s, e, kind in segs:
        body = "\n".join(lines[s:e + 1])
        is_nuxel = ("nuxel-init:" in body) or ("NUXEL_MARKER" in body) or ("nuxel-fb-phone" in body)
        if is_nuxel:
            out.append((s, e))
    return out


def report(lines, s, e, patterns, label):
    print("=" * 78)
    print("%s : lines %d..%d (%d lines)" % (label, s + 1, e + 1, e - s + 1))
    print("=" * 78)
    for name, rx, mode in patterns:
        rx = re.compile(rx)
        hits = [(i + 1, lines[i]) for i in range(s, e + 1) if rx.search(lines[i])]
        if mode == "count":
            print("  %-42s %d" % (name, len(hits)))
        elif mode == "first":
            for ln, txt in hits[:8]:
                print("  %-42s L%-7d %s" % (name, ln, txt.strip()[:130]))
            if len(hits) > 8:
                print("  %-42s … and %d more" % (name, len(hits) - 8))
        elif mode == "all":
            for ln, txt in hits:
                print("  %-42s L%-7d %s" % (name, ln, txt.strip()[:130]))
    print()


PATTERNS = [
    ("initramfs executed",        r"NUXEL_MARKER INITRAMFS_EXECUTED", "first"),
    ("kernel banner",            r"Linux version 4\.14\.253", "first"),
    ("fbdev geometry",           r"FB_SYSFS /sys/class/graphics/fb0/(stride|virtual_size|modes|bits_per_pixel)", "all"),
    ("first light frame",        r"FIRSTLIGHT exit=|FIRSTLIGHT_ANIMATION_DONE|FIRSTLIGHT_FRAME_WRITTEN", "all"),
    ("animation hold pid marker",r"ANIMATION_HOLD_PID=", "all"),
    ("rootfs mounted",           r"NUXEL_MARKER ROOTFS_MOUNTED|ROOTFS_MOUNTED /dev", "first"),
    ("fedora binary executed",   r"NUXEL_MARKER FEDORA_BINARY_EXECUTED", "first"),
    ("systemd lib verified",     r"SYSTEMD_LIB_VERIFIED_PRESENT|SYSTEMD_LIB_INSTALLED_VERIFIED|SYSTEMD_LIB_(IMAGE_MISSING|COPY_FAILED|VERIFY_FAILED)|SYSTEMD_LIB_VERIFY|SYSTEMD_LIB already correct|SYSTEMD_LIB target needs", "all"),
    ("nuxel-verify evidence",    r"NUXEL-VERIFY (sha256|elf)", "first"),
    ("cgroup2 mount",            r"CGROUP2_MOUNT_OK|CGROUP2_MOUNT_FAILED", "all"),
    ("cgroup2 verified",         r"CGROUP2_VERIFIED|CGROUP2_VERIFY_FAILED|CGROUP2_PROC_MOUNTS", "all"),
    ("live console",             r"LIVE_CONSOLE_STARTED|LIVE_CONSOLE binary missing|nuxel-console:", "all"),
    ("boot stage",               r"BOOT_STAGE|BOOT_STAGE_SYSTEM_STARTING", "all"),
    ("systemd started (any)",    r"systemd\[1\]: Started ", "count"),
    ("systemd reached target",   r"systemd\[1\]: Reached target ", "count"),
    ("*** FAILED TO SPAWN EXECUTOR ***", r"Failed to spawn executor", "count"),
    ("failed at step CGROUP",    r"Failed at step CGROUP", "count"),
    ("systemd PID1 banner",      r"systemd\[1\]: systemd \d+\.\d+.*running in system mode", "first"),
    ("udevd alive",              r"systemd-udevd\[", "count"),
    ("journald active",          r"systemd-journald.*(Started|running)", "first"),
    ("dbus-broker active",       r"dbus-broker.*(Started|listening)|Started dbus-broker", "first"),
    ("unit failures (with result)", r"Failed with result", "count"),
    ("operator hard reset / panic", r"hard_reset_hook|kernel BUG|sec_reboot|Kernel panic|restarting system|debug-snapshot: normal reboot", "all"),
    ("watchdog fired",           r"watchdog reset is started|WATCHDOG_FIRED|hard_reset_keys", "all"),
    ("switch_root / handoff",    r"ROOTFS_HANDOFF_STARTED|switching root", "first"),
    ("touchscreen sec_ts",       r"sec_ts_init|sec_tsp|y771|TOUCHSCREEN", "first"),
    ("input devices registered", r"input: .* as /devices/", "all"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("last_kmsg")
    ap.add_argument("--session", type=int, default=None, help="1-based Nuxel session index")
    ap.add_argument("--grep", default=None)
    a = ap.parse_args()

    lines = load(a.last_kmsg)
    segs = segments(lines)
    print("file: %s   lines: %d   S-Boot sessions: %d" % (a.last_kmsg, len(lines), len(segs)))
    for i, (s, e, k) in enumerate(segs, 1):
        print("  seg %2d  L%-7d..%-7d  %s" % (i, s + 1, e + 1, k))
    nx = nuxel_boot_sessions(lines, segs)
    print("\nNuxel boot session(s): %d" % len(nx))
    if not nx:
        print("  (none — this record contains no Nuxel boot)")
        return 1
    for i, (s, e) in enumerate(nx, 1):
        print("  nuxel-%d  L%d..L%d" % (i, s + 1, e + 1))
    print()
    picked = nx if a.session is None else [nx[a.session - 1]]
    for i, (s, e) in enumerate(picked, 1):
        report(lines, s, e, PATTERNS, "NUXEL SESSION")
    if a.grep:
        rx = re.compile(a.grep)
        print("grep %r:" % a.grep)
        for s, e in picked:
            for i in range(s, e + 1):
                if rx.search(lines[i]):
                    print("  L%-7d %s" % (i + 1, lines[i].strip()[:150]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
