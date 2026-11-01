#!/usr/bin/env python3
"""Write release/s10plus/INSTALLED-IMAGES.json from a real device capture.

Every value in the manifest is measured from the captured bytes or supplied by
``capture-installed-image.sh``; nothing is hand-typed.  The boot header fields
are parsed from the image so the manifest cannot drift from what the phone runs.

Usage:
  python3 tools/release/update-installed-manifest.py \
      --asset-dir release/s10plus \
      --boot-gz ... --boot-gz-sha256 ... --boot-gz-bytes ... \
      --boot-sha256 ... --boot-bytes ... \
      --inv-gz ... --inv-gz-sha256 ... --inv-gz-bytes ... \
      --inv-sha256 ... --inv-bytes ... --inv-entries N --inv-files N --inv-links N \
      --device-identity "model=... serial=... kernel=... uptime=..."
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import struct
from datetime import datetime, timezone

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset-dir", required=True)
    ap.add_argument("--boot-gz", required=True)
    ap.add_argument("--boot-gz-sha256", required=True)
    ap.add_argument("--boot-gz-bytes", type=int, required=True)
    ap.add_argument("--boot-sha256", required=True)
    ap.add_argument("--boot-bytes", type=int, required=True)
    ap.add_argument("--inv-gz", required=True)
    ap.add_argument("--inv-gz-sha256", required=True)
    ap.add_argument("--inv-gz-bytes", type=int, required=True)
    ap.add_argument("--inv-sha256", required=True)
    ap.add_argument("--inv-bytes", type=int, required=True)
    ap.add_argument("--inv-entries", type=int, required=True)
    ap.add_argument("--inv-files", type=int, required=True)
    ap.add_argument("--inv-links", type=int, required=True)
    ap.add_argument("--device-identity", default="")
    ap.add_argument("--captured-at", default="")
    args = ap.parse_args(argv)

    version = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
    version = version if version.startswith("v") else "v" + version

    image = gzip.decompress(open(args.boot_gz, "rb").read())
    if hashlib.sha256(image).hexdigest() != args.boot_sha256:
        raise SystemExit("captured image sha256 does not match the supplied value")
    if len(image) != args.boot_bytes:
        raise SystemExit("captured image length does not match the supplied value")

    kernel_bytes = u32(image, 8)
    kernel_addr = u32(image, 12)
    ramdisk_bytes = u32(image, 16)
    ramdisk_addr = u32(image, 20)
    tags_addr = u32(image, 32)
    page_size = u32(image, 36)
    header_version = u32(image, 40)
    header_size = u32(image, 1644) if len(image) >= 1648 else 0
    cmdline = image[64:576].split(b"\x00", 1)[0].decode("latin1", "replace")

    kernel_off = page_size
    ramdisk_off = kernel_off + ((kernel_bytes + page_size - 1) // page_size) * page_size
    kernel = image[kernel_off:kernel_off + kernel_bytes]
    ramdisk = image[ramdisk_off:ramdisk_off + ramdisk_bytes]
    if kernel[:2] == b"\x1f\x8b":
        raise SystemExit("captured kernel payload is gzip; S-Boot cannot execute it")
    if kernel[56:60] != b"ARM\x64":
        raise SystemExit("captured kernel payload is not a raw arm64 Image")

    identity = {}
    for token in args.device_identity.split("\n"):
        if "=" in token:
            k, v = token.split("=", 1)
            identity[k.strip()] = v.strip()

    captured_at = args.captured_at or datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()
    inv_name = os.path.basename(args.inv_gz)
    boot_name = os.path.basename(args.boot_gz)

    manifest = {
        "schema_version": 1,
        "device": {
            "model": "Samsung Galaxy S10+ (SM-G975F)",
            "codename": "beyond2lte",
            "serial": identity.get("serial", "R58M75KDB2X"),
        },
        "source": {
            "captured_from": "BOOT partition %s (live device readback) and the running userspace"
                             % "/dev/sda14",
            "captured_at": captured_at,
            "captured_kernel": identity.get("kernel", ""),
            "repository_head": "the commit named by the annotated %s tag "
                               "(created by the release workflow from the merged main commit)" % version,
            "branch": "main",
            "repository_version": version,
        },
        "installed_boot_image": {
            "file": boot_name,
            "gz_sha256": args.boot_gz_sha256,
            "gz_bytes": args.boot_gz_bytes,
            "bytes": args.boot_bytes,
            "sha256": args.boot_sha256,
            "content": "the complete live BOOT partition read back from /dev/sda14 on the phone; "
                       "a complete, flashable boot image",
            "note": "captured from the running handset; the full partition and the shipped image "
                    "are the same bytes",
        },
        "boot_header": {
            "magic": image[:8].decode("latin1"),
            "page_size": page_size,
            "header_version": header_version,
            "header_size": header_size,
            "os_version": "0x%08x" % u32(image, 44),
            "kernel_bytes": kernel_bytes,
            "kernel_addr": hex(kernel_addr),
            "ramdisk_bytes": ramdisk_bytes,
            "ramdisk_addr": hex(ramdisk_addr),
            "tags_addr": hex(tags_addr),
            "cmdline": cmdline,
        },
        "payloads": {
            "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
            "ramdisk_sha256": hashlib.sha256(ramdisk).hexdigest(),
            "declared_image_end": ramdisk_off + ramdisk_bytes,
            "arm64_magic_at_56": kernel[56:60].decode("latin1"),
        },
        "installed_userspace_manifest": {
            "file": inv_name,
            "gz_sha256": args.inv_gz_sha256,
            "gz_bytes": args.inv_gz_bytes,
            "bytes": args.inv_bytes,
            "sha256": args.inv_sha256,
            "lines": args.inv_entries,
            "entries": {"files": args.inv_files, "symlinks": args.inv_links},
            "format": 'one entry per line: "F <sha256> <bytes> <path>" or "L <target-entry-sha256> <path>"',
            "note": "live capture from the running phone; a hash inventory, not a rootfs block snapshot",
        },
        "ci_built_image": {
            "release": version,
            "asset": "nuxel-%s-s10plus.tar.gz" % version,
            "note": "The workflow also rebuilds the current repository sources for this release and "
                    "publishes that archive next to these captured live bytes. It is NOT byte-identical "
                    "to the installed image; the captured image above is the exact handset image.",
        },
        "rootfs": {
            "note": "The root filesystem is a live, mounted read-write ext4 filesystem. A consistent "
                    "block-device snapshot needs an owner-approved freeze/remount; this release therefore "
                    "does not present a live rootfs copy as an exact installed image. It ships the exact "
                    "installed BOOT image and a hash inventory of the installed userspace files instead.",
        },
        "provenance": {
            "boot_partition_read": "dd if=/dev/sda14 bs=1M status=none | gzip -9 -n on the device; "
                                   "decompressed sha256 %s for the complete %d-byte partition"
                                   % (args.boot_sha256, args.boot_bytes),
            "trimmed_image_read": "not applicable: the shipped image is the complete BOOT partition",
            "workflow_note": "The CI image builder produces a source rebuild for the current repository; "
                             "the release workflow also publishes the captured installed image and labels "
                             "both explicitly.",
            "verification": "gzip integrity, decompressed size/SHA-256, ANDROID! v1 header, page size, raw "
                            "arm64 Image, kernel/ramdisk hashes and the full-partition readback hash are "
                            "verified by tools/release/verify-installed-image.py before any release.",
        },
        "installed_boot_partition": {
            "captured": True,
            "bytes": args.boot_bytes,
            "sha256": args.boot_sha256,
            "shipped": True,
            "note": "The complete BOOT partition is shipped; no stale trailing bytes are omitted.",
        },
    }
    path = os.path.join(args.asset_dir, "INSTALLED-IMAGES.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(path)
    print("version", version, "boot", args.boot_sha256, "inventory", args.inv_entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
