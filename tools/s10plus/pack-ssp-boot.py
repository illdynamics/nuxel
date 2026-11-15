#!/usr/bin/env python3
"""Pack a combined Nuxel S10+ boot image from proven parts (PWNAGE-SSP).

The container is assembled exactly the way the currently-booting image is
laid out.  Rather than re-deriving S-Boot's page rules from a comment, the
layout is *measured* from the donor (the live, verified boot partition):

    start of kernel   = offset of the little-endian arm64 magic "ARMd"
    start of ramdisk  = kernel_start + round_up(header_kernel_size, 2048)
    ramdisk length    = header field 3 (unchanged; S-Boot derives it)
    start of DTB tail = first 0xD00DFEED after the ramdisk

Only the kernel payload changes by default.  The ramdisk (LZMA-alone with the
0xFFFFFFFFFFFFFFFF size field) and the entire DTB/hash tail are copied
byte-for-byte, so every other boot behaviour (NFC/USBNET/DTBO selection)
is preserved.  An optional --initramfs-cpio replaces only the cpio inside the
ramdisk using the same LZMA parameters the installer baked in.

This tool never writes to a device; verify-boot-image.py is the gate.
"""
from __future__ import annotations

import argparse
import hashlib
import lzma
import struct
import sys
from pathlib import Path

MAGIC = b"ANDROID!"
ARM64_MAGIC = b"ARM\x64"
ARM64_MAGIC_OFF = 0x38
FDT_MAGIC = b"\xd0\r\xfe\xed"
PAGE = 2048
LINUX_IMAGE_STEXT = b"\x00\x00\x6c\x14"


def up(n, p=PAGE):
    return (n + p - 1) // p * p


def sha(b):
    return hashlib.sha256(b).hexdigest()


def locate(donor: bytes):
    # Primary rule: the Image entry stub's branch instruction.  The exact
    # opcode is not stable across builds (b vs bl, different jump distance),
    # so a missed literal must not be fatal.  Fall back to the arm64 header
    # magic at +0x38, which every arm64 Image carries.
    kstart = None
    pos = donor.find(LINUX_IMAGE_STEXT)
    while pos >= 0:
        if donor[pos + ARM64_MAGIC_OFF:pos + ARM64_MAGIC_OFF + 4] == ARM64_MAGIC:
            kstart = pos
            break
        pos = donor.find(LINUX_IMAGE_STEXT, pos + 1)
    if kstart is None:
        pos = donor.find(ARM64_MAGIC)
        while pos >= 0:
            cand = pos - ARM64_MAGIC_OFF
            if cand >= 0:
                klen = struct.unpack_from("<I", donor, 8)[0]
                if donor[cand - min(cand, PAGE):cand] or True:
                    kstart = cand
                    break
            pos = donor.find(ARM64_MAGIC, pos + 1)
    if kstart is None:
        raise SystemExit("cannot locate the arm64 Image in the donor")
    (klen, _kaddr, rlen, _raddr) = struct.unpack_from("<IIII", donor, 8)
    rstart = kstart + up(klen)
    ramdisk = donor[rstart:rstart + rlen]
    if not ramdisk or ramdisk[0] != 0x5d:
        raise SystemExit("donor ramdisk is not LZMA-alone (props 0x%02x)"
                         % (ramdisk[0] if ramdisk else -1))
    dtb_at = donor.find(FDT_MAGIC, rstart + rlen)
    if dtb_at < 0:
        raise SystemExit("cannot locate the appended DTB region")
    return kstart, rstart, rlen, ramdisk, dtb_at


def lzma_alone(cpio: bytes) -> bytes:
    filt = [{"id": lzma.FILTER_LZMA1, "preset": 6, "dict_size": 1 << 23}]
    comp = lzma.compress(cpio, format=lzma.FORMAT_ALONE, filters=filt)
    if comp[:1] != b"\x5d":
        raise SystemExit("unexpected LZMA props")
    return comp[:5] + b"\xff" * 8 + comp[13:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", default="backups/boot/boot-orig-20261113.img")
    ap.add_argument("--kernel", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ramdisk-raw", default="",
                    help="replace the compressed ramdisk byte-for-byte")
    ap.add_argument("--initramfs-cpio", default="",
                    help="newc cpio to compress as the new ramdisk")
    ap.add_argument("--ramdisk-align", type=int, default=PAGE)
    ap.add_argument("--manifest", default="")
    ap.add_argument("--pad-to-partition", action="store_true",
                    help="zero-pad to the donor size (flash tool writes a fixed length)")
    a = ap.parse_args(argv)

    donor = Path(a.donor).read_bytes()
    if donor[:8] != MAGIC:
        raise SystemExit("donor is not an Android boot image")
    if b"nuxel.device=s10plus" not in donor[64:576]:
        raise SystemExit("donor is not a Nuxel S10+ boot image")
    kstart, rstart, rlen, ramdisk, dtb_at = locate(donor)
    (klen0, kaddr, rlen0, raddr) = struct.unpack_from("<IIII", donor, 8)
    hdr = bytearray(donor[:kstart])
    tail = donor[dtb_at:]

    if a.ramdisk_raw:
        ramdisk = Path(a.ramdisk_raw).read_bytes()
    elif a.initramfs_cpio:
        cpio = Path(a.initramfs_cpio).read_bytes()
        if cpio[:6] != b"070701":
            raise SystemExit("--initramfs-cpio is not newc (070701)")
        ramdisk = lzma_alone(cpio)
    if ramdisk[0] != 0x5d:
        raise SystemExit("ramdisk is not LZMA-alone")
    if a.ramdisk_align > 1 and len(ramdisk) % a.ramdisk_align:
        ramdisk += b"\x00" * (a.ramdisk_align - len(ramdisk) % a.ramdisk_align)

    kernel = Path(a.kernel).read_bytes()
    if kernel[ARM64_MAGIC_OFF:ARM64_MAGIC_OFF + 4] != ARM64_MAGIC:
        raise SystemExit("kernel is not a raw little-endian arm64 Image")
    # Header layout (v1): +0x08 kernel size, +0x0c kernel load address,
    # +0x10 ramdisk size, +0x14 ramdisk load address (+0x18 second size).
    # This file used to write a "<II" pair at +0x08, which also overwrote
    # the kernel load address with the ramdisk length; the resulting image
    # had kaddr ≈ 0x250000 instead of 0x10008000 and never booted.  Only the
    # two size fields may change here - addresses are inherited from the
    # donor and are what S-Boot uses to place Image and the ramdisk.
    struct.pack_into("<I", hdr, 8, len(kernel))
    struct.pack_into("<I", hdr, 0x10, rlen)
    assert struct.unpack_from("<I", hdr, 0x0c)[0] == kaddr, "kernel addr disturbed"
    assert struct.unpack_from("<I", hdr, 0x14)[0] == raddr, "ramdisk addr disturbed"

    out = bytes(hdr) + kernel + b"\0" * (up(len(kernel)) - len(kernel)) + ramdisk
    pad = (dtb_at - len(out)) % PAGE
    out += b"\0" * pad + tail
    if len(out) > len(donor):
        raise SystemExit(
            "image does not fit the boot partition: %d bytes > %d "
            "(kernel %d + ramdisk %d + dtb %d); flashing it would truncate "
            "the appended DTB or overflow the partition"
            % (len(out), len(donor), len(kernel), len(ramdisk), len(tail)))
    if a.pad_to_partition and len(out) < len(donor):
        out += b"\0" * (len(donor) - len(out))
    Path(a.out).write_bytes(out)

    facts = {
        "image": a.out,
        "sha256": sha(out),
        "size": len(out),
        "header_bytes": kstart,
        "kernel_offset": kstart,
        "kernel_size": len(kernel),
        "kernel_sha256": sha(kernel),
        "ramdisk_offset": kstart + up(len(kernel)),
        "ramdisk_size": len(ramdisk),
        "ramdisk_sha256": sha(ramdisk),
        "dtb_offset": kstart + up(len(kernel)) + len(ramdisk) + pad,
        "dtb_region_size": len(tail),
        "dtb_region_sha256": sha(tail),
        "kernel_addr": hex(kaddr),
        "ramdisk_addr": hex(raddr),
        "cmdline": donor[64:576].split(b"\0")[0].decode(),
    }
    for k, v in facts.items():
        print("%-18s %s" % (k, v))
    if a.manifest:
        Path(a.manifest).write_text(
            "\n".join("%-18s %s" % (k, v) for k, v in facts.items()) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
