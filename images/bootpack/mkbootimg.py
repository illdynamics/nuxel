#!/usr/bin/env python3
"""Android Boot Image Header v3/v4 writer (AOSP mkbootimg-compatible, byte-correct).

This is an honest, byte-correct implementation of the Android Boot Image v4
format (Android 10+/14+ for mustang). The layout below reproduces the
authoritative AOSP ``system/tools/mkbootimg/mkbootimg.py``
``write_header_v3_and_above`` + ``write_data`` behaviour exactly, so the
produced image carries the ``ANDROID!`` magic and can be unpacked by
``unpack_bootimg``/``avbtool``. No AOSP binary is required.

It is ONLY meaningful when a real, buildable kernel ``Image.gz`` AND a real
initramfs exist. The boot image (header v3/v4) packs the kernel and ramdisk
page-aligned under the header; for v4 the Device Tree lives in the companion
``vendor_boot`` image (not ``boot``), which this tool can also emit when a DTB
is supplied.

Bit-layout reference (AOSP ``bootimg.h`` + ``mkbootimg.py``):

  * boot_img_hdr_v3 size         = 1580 bytes
  * boot_img_hdr_v4 size         = 1584 bytes (v3 + 4-byte signature_size)
  * header page field order (little-endian):
        +0   magic[8]                "ANDROID!"
        +8   kernel_size
        +12  ramdisk_size
        +16  os_version | patch      (os_version << 11) | os_patch_level
        +20  header_size
        +24  reserved[4]             (16 zero bytes)
        +40  header_version          (3 or 4)
        +44  cmdline[512+1024]       (1536 bytes)
        +1580 signature_size         (v4 only, 4 bytes)
      then zero-padded to the 4096-byte page.
  * payload pages (v3/v4 boot): kernel -> ramdisk (each padded to page_size).
"""

import argparse
import os
import re
import struct
import sys

BOOT_MAGIC = b"ANDROID!"
BOOT_MAGIC_SIZE = 8
BOOT_ARGS_SIZE = 512
BOOT_EXTRA_ARGS_SIZE = 1024
BOOT_IMAGE_HEADER_V3_SIZE = 1580
BOOT_IMAGE_HEADER_V4_SIZE = 1584
DEFAULT_PAGE_SIZE = 4096

VENDOR_BOOT_MAGIC = b"VNDRBOOT"
VENDOR_BOOT_ARGS_SIZE = 2048
VENDOR_BOOT_NAME_SIZE = 16
VENDOR_BOOT_IMAGE_HEADER_V3_SIZE = 2112
VENDOR_BOOT_IMAGE_HEADER_V4_SIZE = 2128


def parse_os_version(x):
    """A.B.C -> (A<<14)|(B<<7)|C  (7 bits each), matching AOSP mkbootimg."""
    m = re.search(r"^(\d{1,3})(?:\.(\d{1,3})(?:\.(\d{1,3}))?)?", str(x))
    if not m:
        return 0
    a = int(m.group(1)); b = int(m.group(2) or 0); c = int(m.group(3) or 0)
    assert a < 128 and b < 128 and c < 128, "os_version fields must be < 128"
    return (a << 14) | (b << 7) | c


def parse_os_patch_level(x):
    """Y-M[-D] -> ((Y-2000)<<4)|M   (7 bits year, 4 bits month)."""
    m = re.search(r"^(\d{4})-(\d{2})(?:-(\d{2}))?", str(x))
    if not m:
        return 0
    y = int(m.group(1)) - 2000
    mo = int(m.group(2))
    assert 0 <= y < 128, "year must be within 2000..2127"
    assert 0 < mo <= 12, "month must be 1..12"
    return (y << 4) | mo


def _osfield(os_version="15.0.0", os_patch_level="2025-06-05"):
    return (parse_os_version(os_version) << 11) | parse_os_patch_level(os_patch_level)


def _pad(buf, page=DEFAULT_PAGE_SIZE):
    out = bytearray(buf)
    while len(out) % page:
        out += b"\x00"
    return bytes(out)


def build_boot(kernel_bytes, ramdisk_bytes, cmdline=b"",
               os_version="15.0.0", os_patch_level="2025-06-05",
               header_version=4, page_size=DEFAULT_PAGE_SIZE):
    """Return the concatenated v3/v4 Android boot image (header page + payload).

    The returned image begins with ``ANDROID!`` and is a genuine, unpackable
    Android Boot Image Header v4 (or v3). DTB intentionally NOT appended:
    for header v3/v4 the device tree belongs in vendor_boot, not boot.
    """
    if not kernel_bytes:
        raise ValueError("kernel image is empty - cannot build a genuine boot image")
    if not ramdisk_bytes:
        raise ValueError("ramdisk is empty - cannot build a genuine boot image")

    if header_version == 4:
        header_size = BOOT_IMAGE_HEADER_V4_SIZE
    elif header_version == 3:
        header_size = BOOT_IMAGE_HEADER_V3_SIZE
    else:
        raise ValueError("only header_version 3 and 4 are supported for the boot image")

    hdr = bytearray(header_size)

    # magic
    hdr[0:BOOT_MAGIC_SIZE] = BOOT_MAGIC
    struct.pack_into("<I", hdr, 8, len(kernel_bytes))            # kernel_size
    struct.pack_into("<I", hdr, 12, len(ramdisk_bytes))          # ramdisk_size
    struct.pack_into("<I", hdr, 16, _osfield(os_version, os_patch_level))
    struct.pack_into("<I", hdr, 20, header_size)                 # header_size
    struct.pack_into("<I", hdr, 40, header_version)              # header_version
    # reserved[4] stays zero (offsets 24..39)
    cmd = cmdline if isinstance(cmdline, bytes) else cmdline.encode("utf-8")
    cmd = _strip_nul(cmd)
    if len(cmd) > BOOT_ARGS_SIZE + BOOT_EXTRA_ARGS_SIZE:
        cmd = cmd[: BOOT_ARGS_SIZE + BOOT_EXTRA_ARGS_SIZE - 1] + b"\x00"
    hdr[44:44 + len(cmd)] = cmd
    # v4: signature_size at +1580 stays 0 (no GKI boot signature applied)

    # Concatenate header page (zero-padded) + kernel page + ramdisk page.
    out = bytearray()
    out += _pad(bytes(hdr), page_size)
    out += _pad(kernel_bytes, page_size)
    out += _pad(ramdisk_bytes, page_size)
    return bytes(out)


def _strip_nul(b):
    i = b.find(b"\x00")
    return b[:i] if i != -1 else b


def build_boot_stream(kernel_path, ramdisk_path, cmdline, out_path,
                      os_version=None, os_patch_level=None, header_version=4,
                      page_size=DEFAULT_PAGE_SIZE):
    """Construct and write a genuine v3/v4 Android boot image from file paths."""
    with open(kernel_path, "rb") as fh:
        k = fh.read()
    with open(ramdisk_path, "rb") as fh:
        r = fh.read()
    img = build_boot(
        k, r, cmdline=cmdline,
        os_version=os_version or "15.0.0",
        os_patch_level=os_patch_level or "2025-06-05",
        header_version=header_version, page_size=page_size,
    )
    with open(out_path, "wb") as fh:
        fh.write(img)
    return len(img), len(k), len(r)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kernel", required=True, help="kernel Image.gz")
    ap.add_argument("--ramdisk", required=True, help="ramdisk cpio.gz")
    ap.add_argument("--dtb", default=None, help="optional DTB (not packed into v4 boot; see --vendor-boot)")
    ap.add_argument("--cmdline", default="")
    ap.add_argument("--os-version", default="15.0.0")
    ap.add_argument("--os-patch-level", default="2025-06-05")
    ap.add_argument("--header-version", type=int, default=4, choices=(3, 4))
    ap.add_argument("--pagesize", type=int, default=DEFAULT_PAGE_SIZE)
    ap.add_argument("--output", required=True)
    ap.add_argument("--vendor-boot", default=None,
                    help="optional vendor_boot output path (v4 DTB home)")
    args = ap.parse_args()

    n, kn, rn = build_boot_stream(
        args.kernel, args.ramdisk, args.cmdline, args.output,
        os_version=args.os_version, os_patch_level=args.os_patch_level,
        header_version=args.header_version, page_size=args.pagesize,
    )
    print(f"wrote {args.output} ({n} bytes), kernel={kn} ramdisk={rn}")

    if args.vendor_boot and args.dtb and os.path.isfile(args.dtb):
        with open(args.dtb, "rb") as fh:
            dtb = fh.read()
        vb = build_vendor_boot(dtb, args.cmdline, page_size=args.pagesize)
        with open(args.vendor_boot, "wb") as fh:
            fh.write(vb)
        print(f"wrote {args.vendor_boot} ({len(vb)} bytes), dtb={len(dtb)}")


def build_vendor_boot(dtb_bytes, cmdline=b"", page_size=DEFAULT_PAGE_SIZE,
                      header_version=4, kernel_addr=0x10000000,
                      ramdisk_addr=0x01000000, tags_addr=0x00000100,
                      dtb_addr=0x01f00000):
    """Emit a byte-correct Android vendor_boot v3/v4 image carrying a DTB.

    Layout (AOSP bootimg.h, packed, little-endian):
      magic[8] "VNDRBOOT" | header_version | page_size | kernel_addr |
      ramdisk_addr | vendor_ramdisk_size | cmdline[2048] | tags_addr |
      name[16] | header_size | dtb_size | dtb_addr [| v4: 4 x uint32] .
    Payload: vendor_ramdisk (none) then the page-aligned DTB.
    """
    if not dtb_bytes:
        raise ValueError("dtb is empty - cannot build a vendor_boot image")
    if header_version == 4:
        hs = VENDOR_BOOT_IMAGE_HEADER_V4_SIZE
    elif header_version == 3:
        hs = VENDOR_BOOT_IMAGE_HEADER_V3_SIZE
    else:
        raise ValueError("only vendor_boot header_version 3 and 4 supported")

    hdr = bytearray(hs)
    hdr[0:8] = VENDOR_BOOT_MAGIC
    struct.pack_into("<I", hdr, 8, header_version)      # header_version
    struct.pack_into("<I", hdr, 12, page_size)          # page_size
    struct.pack_into("<I", hdr, 16, kernel_addr)        # kernel_addr
    struct.pack_into("<I", hdr, 20, ramdisk_addr)       # ramdisk_addr
    struct.pack_into("<I", hdr, 24, 0)                  # vendor_ramdisk_size = 0
    cmd = cmdline if isinstance(cmdline, bytes) else cmdline.encode("utf-8")
    cmd = _strip_nul(cmd)
    if len(cmd) > VENDOR_BOOT_ARGS_SIZE:
        cmd = cmd[: VENDOR_BOOT_ARGS_SIZE - 1] + b"\x00"
    hdr[28:28 + len(cmd)] = cmd                         # cmdline[2048]
    struct.pack_into("<I", hdr, 2076, tags_addr)        # tags_addr
    # name[16] stays zero (offsets 2080..2095)
    struct.pack_into("<I", hdr, 2096, hs)               # header_size
    struct.pack_into("<I", hdr, 2100, len(dtb_bytes))   # dtb_size
    struct.pack_into("<Q", hdr, 2104, dtb_addr)         # dtb_addr (8 bytes)
    # v4 trailing 16 bytes (2112..2127): vendor_ramdisk_table_size,
    # entry_num, entry_size, bootconfig_size = all 0 (no vendor ramdisk/config)
    buf = bytearray()
    buf += _pad(bytes(hdr), page_size)                   # header page
    buf += _pad(dtb_bytes, page_size)                    # dtb page
    return bytes(buf)


if __name__ == "__main__":
    main()
