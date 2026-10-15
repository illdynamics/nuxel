#!/usr/bin/env python3
"""unpack-boot-image.py — split an Android v1 boot image into its sections.

Writes kernel / ramdisk (decompressed to the raw newc cpio) / dtb plus a JSON
summary.  Used by boot/s10plus/build-candidate.sh so that every derived
candidate is built from a byte-exact copy of a hardware-proven container.

Usage: unpack-boot-image.py IMAGE OUTDIR
"""

import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc  # noqa: E402


def decompress_ramdisk(blob):
    if blob[:2] == b"\x1f\x8b":
        import gzip
        return gzip.decompress(blob), "gzip"
    if blob[:3] == b"\x5d\x00\x00":
        import lzma
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        return dec.decompress(blob), "lzma-alone"
    if blob[:6] == b"\xfd7zXZ\x00":
        import lzma
        return lzma.decompress(blob, format=lzma.FORMAT_XZ), "xz"
    if blob[:3] == b"BZh":
        import bz2
        return bz2.decompress(blob), "bzip2"
    if blob[:6] == b"070701":
        return blob, "none"
    raise SystemExit("unrecognised ramdisk container: %s" % blob[:8].hex())


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: unpack-boot-image.py IMAGE OUTDIR")
    path, outdir = argv
    data = open(path, "rb").read()
    if data[:8] != b"ANDROID!":
        raise SystemExit("not an Android boot image")
    f32 = lambda o: struct.unpack_from("<I", data, o)[0]
    ksize, kaddr, rsize, raddr = f32(8), f32(12), f32(16), f32(20)
    tags, page = f32(32), f32(36)
    field40, os_version = f32(40), f32(44)
    if page != 2048:
        raise SystemExit("page_size %d unsupported" % page)
    round_up = lambda v: (v + page - 1) // page * page
    koff = page
    roff = koff + round_up(ksize)
    doff = roff + round_up(rsize)
    kernel = data[koff:koff + ksize]
    ramdisk = data[roff:roff + rsize]
    dtb = data[doff:]
    os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, "Image"), "wb").write(kernel)
    plain, fmt = decompress_ramdisk(ramdisk)
    open(os.path.join(outdir, "initramfs.cpio"), "wb").write(plain)
    open(os.path.join(outdir, "ramdisk.raw"), "wb").write(ramdisk)
    with open(os.path.join(outdir, "appended.dtb"), "wb") as fh:
        fh.write(dtb)
    summary = {
        "source": os.path.abspath(path),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "header": {"kernel_size": ksize, "kernel_addr": "0x%08x" % kaddr,
                   "ramdisk_size": rsize, "ramdisk_addr": "0x%08x" % raddr,
                   "tags_addr": "0x%08x" % tags, "page_size": page,
                   "header_field40": field40, "os_version": "0x%08x" % os_version},
        "offsets": {"kernel": koff, "ramdisk": roff, "dtb": doff},
        "ramdisk_container": fmt,
        "ramdisk_uncompressed_size": len(plain),
        "dtb_size": len(dtb),
        "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
        "initramfs_cpio_sha256": hashlib.sha256(plain).hexdigest(),
        "appended_dtb_sha256": hashlib.sha256(dtb).hexdigest(),
        "cpio_records": sum(1 for _ in newc.iter_records(plain)),
    }
    with open(os.path.join(outdir, "sections.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
