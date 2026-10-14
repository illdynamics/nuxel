#!/usr/bin/env python3
"""make-initramfs.py -- rebuild the Nuxel g7power initramfs (newc cpio) from an
existing ramdisk, replacing /init and ensuring the toybox applet symlinks exist.

Root cause this fixes: the shipped initramfs contained `init` (a #!/bin/sh
script) and `bin/toybox`, but NO `bin/sh` and NO applet symlinks (mount, blkid,
switch_root, ...).  The kernel therefore could not exec /init at all
("No working init found") -> no userspace -> bootloop.  The init's own
symlink-creation block was guarded by `[ ! -e /bin/sh ]`, so it could never
create them either.

Usage: make-initramfs.py --in <ramdisk.cpio.gz> --init <init script> --out <out.cpio.gz>
"""
import argparse, gzip, os, struct, sys

APPLETS = ["sh", "mount", "umount", "switch_root", "modprobe", "insmod", "mknod",
           "ls", "cat", "printf", "echo", "sed", "grep", "awk", "find", "sleep",
           "date", "ps", "df", "du", "sync", "reboot", "poweroff", "dd", "cp",
           "mv", "rm", "mkdir", "ln", "chown", "chmod", "dmesg", "blkid",
           "head", "tail", "tr", "cut", "wc", "uname", "mkswap", "losetup",
           "mkfs.ext4", "tar", "gzip"]

def parse(buf):
    entries = []  # (name, mode, data)
    off = 0
    while off < len(buf):
        if buf[off:off+6] not in (b"070701", b"070702"):
            break
        f = [int(buf[off+6+i*8:off+6+i*8+8], 16) for i in range(13)]
        mode = f[1]; filesize = f[6]; namesize = f[11]
        name = buf[off+110:off+110+namesize-1].decode("latin1")
        doff = (off + 110 + namesize + 3) & ~3
        data = buf[doff:doff+filesize]
        if name != "TRAILER!!!":
            entries.append((name, mode, data))
        off = (doff + filesize + 3) & ~3
        if name == "TRAILER!!!":
            break
    return entries

def emit(entries, out):
    buf = bytearray()
    ino = 1
    def wr(name, mode, data):
        nonlocal ino
        nb = name.encode() + b"\x00"
        buf.extend(b"070701")
        buf.extend(("%08X" % ino).encode())
        for v in (mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(nb), 0):
            buf.extend(("%08X" % v).encode())
        buf.extend(nb)
        while len(buf) % 4:
            buf.append(0)
        buf.extend(data)
        while len(buf) % 4:
            buf.append(0)
        ino += 1
    for name, mode, data in entries:
        wr(name, mode, data)
    # TRAILER
    buf.extend(b"070701")
    buf.extend(b"0" * 8 * 13)
    buf.extend(b"TRAILER!!!\x00")
    while len(buf) % 4:
        buf.append(0)
    with open(out, "wb") as f:
        f.write(gzip.compress(bytes(buf), 9))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--init", dest="init", required=True)
    ap.add_argument("--out", dest="out", required=True)
    a = ap.parse_args()
    buf = gzip.decompress(open(a.inp, "rb").read())
    entries = parse(buf)
    init = open(a.init, "rb").read()
    HAVE = {n for n, _, _ in entries}
    new = []
    for name, mode, data in entries:
        if name == "init":
            data = init
        new.append((name, mode, data))
    # symlink helper: newc symlink mode 0120777, data = target
    def symlink(name, target):
        return (name, 0o120777, target.encode())
    if "bin" not in HAVE:
        new.append(("bin", 0o040755, b""))
    added = []
    if "bin/toybox" not in HAVE:
        sys.exit("bin/toybox missing from source ramdisk")
    for app in APPLETS:
        path = "bin/" + app
        if path not in HAVE:
            new.append(symlink(path, "toybox"))
            added.append(app)
    # also a sbin with the same applets, harmless and helps PATH=/sbin
    if "sbin" not in HAVE:
        new.append(("sbin", 0o040755, b""))
    emit(new, a.out)
    print("wrote %s" % a.out)
    print("added symlinks: %s" % (" ".join(added) or "(none)"))
    print("entries: %d, init size: %d" % (len(new), len(init)))

if __name__ == "__main__":
    main()
