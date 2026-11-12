#!/usr/bin/env python3
"""Repack a Samsung/Android boot v1 image with a new kernel (and optional DTB).

Keeps the ramdisk, load addresses, os_version and command line of the donor
image byte-for-byte; only the kernel payload (and, when given, the appended
DTB) is replaced.  Used for incremental NFC bring-up: the boot partition is the
only thing that changes, so no reflash of the rootfs is involved.

  pack-boot-v1.py DONOR_IMAGE KERNEL_IMAGE.gz OUTPUT_IMAGE [--dtb FILE]
"""
import argparse
import struct
import sys

PAGE = 2048
HDR_SIZE = 1648


def pad(n, page=PAGE):
    return (n + page - 1) // page * page


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("donor")
    ap.add_argument("kernel")
    ap.add_argument("output")
    ap.add_argument("--dtb")
    a = ap.parse_args(argv)

    d = open(a.donor, "rb").read()
    header = bytearray(d[:HDR_SIZE])
    (magic, klen, kaddr, rlen, raddr, second, saddr, tags,
     page, hver, ver) = struct.unpack_from("<8s10I", d)
    # boot v1: dt_size lives in the v1 extension, not field 9 (which is 0).
    (dtlen,) = struct.unpack_from("<I", d, 40)
    if magic != b"ANDROID!" or page != PAGE or second != 0:
        raise SystemExit("unexpected Android boot v1 format")
    if b"nuxel.device=s10plus" not in d[64:576]:
        raise SystemExit("donor is not a Nuxel S10+ boot image")

    koff = PAGE
    r = d[koff + pad(klen):koff + pad(klen) + rlen]
    dt = open(a.dtb, "rb").read() if a.dtb else d[koff + pad(klen) + pad(rlen):][:dtlen]
    k = open(a.kernel, "rb").read()

    struct.pack_into("<10I", header, 8, len(k), kaddr, len(r), raddr,
                     0, saddr, tags, PAGE, len(dt), ver)

    out = bytes(header) + b"\0" * (PAGE - HDR_SIZE)
    out += k + b"\0" * (pad(len(k)) - len(k))
    out += r + b"\0" * (pad(len(r)) - len(r))
    out += dt
    open(a.output, "wb").write(out)
    print("kaddr=0x%x raddr=0x%x tags=0x%x kernel=%d ramdisk=%d dtb=%d total=%d"
          % (kaddr, raddr, tags, len(k), len(r), len(dt), len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
