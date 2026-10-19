#!/usr/bin/env python3
"""mkinitramfs-cpio.py — deterministic newc cpio from a staging tree.

Thin, explicit wrapper around images/bootpack/cpio_builder.build_cpio (pure
stdlib) so the S10+ initramfs can be packed identically on macOS (where there
is no `cpio`) and on the Linux runner.  Directory order, inode order and mtime
are fixed, so the same tree always yields the same archive.

Usage:
    python3 tools/s10plus/mkinitramfs-cpio.py --tree DIR --out FILE [--mtime 0]

Exit: 0 ok, 1 IO/format error, 2 usage.
"""
import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "images", "bootpack")))

from cpio_builder import build_cpio  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mkinitramfs-cpio.py")
    ap.add_argument("--tree", required=True, help="staging root")
    ap.add_argument("--out", required=True, help="output newc archive")
    ap.add_argument("--mtime", type=int, default=0, help="fixed mtime (default 0)")
    a = ap.parse_args(argv)

    if not os.path.isdir(a.tree):
        print("no such staging tree: %s" % a.tree, file=sys.stderr)
        return 2
    if os.path.exists(a.out):
        os.unlink(a.out)

    buf = io.BytesIO()
    n = build_cpio(a.tree, buf, fixed_mtime=a.mtime)
    blob = buf.getvalue()
    with open(a.out, "wb") as fh:
        fh.write(blob)
    print("mkinitramfs-cpio: %s -> %s (%d records, %d bytes)"
          % (a.tree, a.out, n, len(blob)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
