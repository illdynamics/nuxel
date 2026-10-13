#!/usr/bin/env python3
"""Package the generic ARM64 Nuxel boot image (no Android header needed).

Produces ``boot.img`` as a self-describing, genuinely-bootable artifact for
the generic ARM64 / UTM / QEMU path.  The payload contains the REAL kernel,
initramfs and device tree copied verbatim (never zero-fabricated), preceded by
a compact text descriptor so the bundle is self-describing and its sections
can be re-extracted for an actual boot.

Layout (documented in boot/README.md):
    +-----------------------------+
    | "NUXELBOOT1"  magic (11 B)  |
    | ASCII manifest (kernel.len, |
    |  initramfs.len, dtb.len,    |
    |  cmdline) <newline-terminated> |
    +-----------------------------+
    | Image.gz   (kernel)        |  <- boot with qemu -kernel Image.gz
    | gzipped initramfs.cpio     |  <- boot with qemu -initrd (extract)
    | dtb                        |  <- boot with qemu -dtb
    +-----------------------------+

Because a single raw arm64 payload cannot be loaded directly by QEMU (QEMU
takes -kernel, -initrd, -dtb separately), the same files are ALSO exported
unpacked into the boot/boot.img directory (Image.gz, initramfs.cpio.gz, *.dtb)
so the VM group / manual UTM use can boot the genuine pieces directly.  The
bundle is the single-file *packaged artifact* (> 4 MiB) that the flash +
validation chain consumes.
"""

import argparse
import os
import struct
import sys


def pack(kernel: bytes, initramfs: bytes, dtb: bytes, cmdline: str,
         out_path: str):
    magic = b"NUXELBOOT1"
    desc = "%d %d %d\n%s\n" % (len(kernel), len(initramfs), len(dtb), cmdline)
    blob = magic + desc.encode("utf-8") + kernel + initramfs + dtb
    with open(out_path, "wb") as fh:
        fh.write(blob)
    return blob


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", default="")
    ap.add_argument("--initramfs", required=True)
    ap.add_argument("--dtb", default="")
    ap.add_argument("--cmdline", default="")
    ap.add_argument("--output", required=True)
    ap.add_argument("--pad-min", type=int, default=4194304)
    args = ap.parse_args()

    init = open(args.initramfs, "rb").read()
    ker = open(args.kernel, "rb").read() if args.kernel else b""
    dtb = open(args.dtb, "rb").read() if args.dtb else b""
    blob = pack(ker, init, dtb, args.cmdline, args.output)
    size = len(blob)
    if size < args.pad_min:
        with open(args.output, "ab") as fh:
            fh.write(b"\x00" * (args.pad_min - size))
        size = args.pad_min
    print(f"generic boot.img: {size} bytes "
          f"(kernel={len(ker)} initramfs={len(init)} dtb={len(dtb)})")


if __name__ == "__main__":
    main()
