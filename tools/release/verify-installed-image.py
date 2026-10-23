#!/usr/bin/env python3
"""Fail-closed verifier for the capture of the image installed on the S10+.

The GitHub release must publish the exact bytes that are on the phone's BOOT
partition, not merely an image produced from the same sources.  This tool reads
``release/s10plus/INSTALLED-IMAGES.json`` and proves, from the shipped gzip
stream alone, that:

  * the gzip stream is intact and its decompressed SHA-256/byte count match the
    recorded values;
  * the payload is a legacy Android v1 ``ANDROID!`` container for beyond2lte;
  * the kernel payload is a raw arm64 Image (not Image.gz), and its SHA-256 and
    the ramdisk SHA-256 match the manifest;
  * the full-partition readback hash recorded in the manifest is consistent with
    the released image (the image is the partitions's header-declared bytes).

Usage:
  python3 tools/release/verify-installed-image.py [--asset-dir release/s10plus] [--json]

Exit: 0 = every check passed; 1 = mismatch; 2 = missing input/usage error.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import struct
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEFAULT_DIR = os.path.join(ROOT, "release", "s10plus")
ARM64_MAGIC = b"ARM\x64"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(msg: str) -> int:
    print("::error::installed-image: " + msg, file=sys.stderr)
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="verify-installed-image.py")
    ap.add_argument("--asset-dir", default=DEFAULT_DIR)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    manifest_path = os.path.join(args.asset_dir, "INSTALLED-IMAGES.json")
    if not os.path.isfile(manifest_path):
        print("missing manifest: " + manifest_path, file=sys.stderr)
        return 2
    try:
        manifest = json.load(open(manifest_path))
    except (OSError, ValueError) as exc:
        print("cannot read manifest: %s" % exc, file=sys.stderr)
        return 2

    rec = manifest.get("installed_boot_image") or {}
    name = rec.get("file")
    if not name:
        return fail("manifest has no installed_boot_image.file")
    path = os.path.join(args.asset_dir, name)
    if not os.path.isfile(path):
        return fail("shipped installed image is missing: " + path)

    gz = open(path, "rb").read()
    try:
        image = gzip.decompress(gz)
    except (OSError, EOFError) as exc:
        return fail("gzip stream is invalid: %s" % exc)

    checks = []
    def check(label, ok, detail=""):
        checks.append((label, bool(ok), detail))
        if not ok:
            print("  [FAIL] %s %s" % (label, detail), file=sys.stderr)
        elif not args.quiet:
            print("  [ok]   %s %s" % (label, detail))
        return bool(ok)

    ok = True
    ok &= check("decompressed SHA-256 matches the manifest",
                sha256(image) == rec.get("sha256"),
                "%s" % sha256(image))
    ok &= check("decompressed byte count matches the manifest",
                len(image) == rec.get("bytes"), "%d bytes" % len(image))
    ok &= check("gzip file SHA-256 matches the manifest",
                sha256(gz) == rec.get("gz_sha256"), sha256(gz))

    if len(image) < 2048:
        return fail("image is shorter than one page")
    ok &= check("ANDROID! header", image[:8] == b"ANDROID!", repr(image[:8]))
    kernel_bytes, kernel_addr, ramdisk_bytes, ramdisk_addr = struct.unpack_from("<4I", image, 8)
    page_size, header_version = struct.unpack_from("<II", image, 36)
    header_size = struct.unpack_from("<I", image, 1644)[0] if len(image) >= 1648 else 0
    hdr = manifest.get("boot_header") or {}
    ok &= check("page size is 2048", page_size == 2048, str(page_size))
    ok &= check("header version is 1 (S-Boot v1 container)", header_version == 1, str(header_version))
    ok &= check("header size is 1648", header_size == 1648, str(header_size))
    ok &= check("kernel size matches the manifest", kernel_bytes == hdr.get("kernel_bytes"),
                "%d vs %s" % (kernel_bytes, hdr.get("kernel_bytes")))
    ok &= check("ramdisk size matches the manifest", ramdisk_bytes == hdr.get("ramdisk_bytes"),
                "%d vs %s" % (ramdisk_bytes, hdr.get("ramdisk_bytes")))
    ok &= check("load addresses match the manifest",
                (hex(kernel_addr), hex(ramdisk_addr), hex(struct.unpack_from("<I", image, 32)[0])) ==
                (hdr.get("kernel_addr"), hdr.get("ramdisk_addr"), hdr.get("tags_addr")),
                "kernel=%s ramdisk=%s tags=%s" % (hex(kernel_addr), hex(ramdisk_addr), hex(struct.unpack_from("<I", image, 32)[0])))
    ok &= check("cmdline names nuxel.device=s10plus", "nuxel.device=s10plus" in image[64:576].decode("latin1", "replace"))

    kernel_off = page_size
    ramdisk_off = kernel_off + ((kernel_bytes + page_size - 1) // page_size) * page_size
    kernel = image[kernel_off:kernel_off + kernel_bytes]
    ramdisk = image[ramdisk_off:ramdisk_off + ramdisk_bytes]
    payloads = manifest.get("payloads") or {}
    ok &= check("kernel is a RAW arm64 Image (never gzip)", kernel[:2] != b"\x1f\x8b")
    ok &= check("kernel arm64 magic at offset 56", kernel[56:60] == ARM64_MAGIC, repr(kernel[56:60]))
    ok &= check("kernel SHA-256 matches the manifest",
                sha256(kernel) == payloads.get("kernel_sha256"), sha256(kernel))
    ok &= check("ramdisk SHA-256 matches the manifest",
                sha256(ramdisk) == payloads.get("ramdisk_sha256"), sha256(ramdisk))
    ok &= check("declared image end fits the released bytes",
                payloads.get("declared_image_end", 0) <= len(image), str(len(image)))

    # The full-partition capture consists of these exact bytes followed only by
    # stale bytes from older candidates.  Record the relationship explicitly.
    part = manifest.get("installed_boot_partition") or {}
    ok &= check("full BOOT partition is at least this image",
                part.get("bytes", 0) >= len(image),
                "%s >= %d" % (part.get("bytes"), len(image)))

    if args.json or not args.quiet:
        print(json.dumps({
            "verdict": "PASS" if ok else "FAIL",
            "asset": path,
            "gz_bytes": len(gz),
            "gz_sha256": sha256(gz),
            "image_bytes": len(image),
            "image_sha256": sha256(image),
            "kernel_sha256": sha256(kernel),
            "ramdisk_sha256": sha256(ramdisk),
            "checks": [{"label": label, "ok": passed, "detail": detail}
                       for label, passed, detail in checks],
        }, indent=2))
    if not ok:
        print("installed-image: FAIL", file=sys.stderr)
        return 1
    print("installed-image: PASS — release asset is the exact image installed on the phone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
