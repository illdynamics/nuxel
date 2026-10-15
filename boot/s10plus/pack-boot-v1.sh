#!/usr/bin/env python3
"""pack-boot-v1.sh — legacy Android boot image (header v1) packer for S10+.

This tool is COMPLETELY separate from images/bootpack/mkbootimg.py (which
handles v3/v4 boot images only). The Samsung Galaxy S10+ (beyond2lte) boots a
legacy v1 boot image with page_size 2048 and "ANDROID!" magic — S-Boot reads
this format, so both the Nuxel kernel image and the U-Boot chainload image are
wrapped as v1 boot images.

Header layout (struct boot_img_hdr_v1, little-endian):
  magic[8]       = "ANDROID!"
  kernel_size    = <kernel image size in bytes>
  kernel_addr    = <load address>
  ramdisk_size   = <ramdisk size in bytes>
  ramdisk_addr   = <ramdisk load address>
  second_size    = 0
  second_addr    = 0
  tags_addr      = <ATAGS/DTB address>
  page_size      = 2048
  dt_size        = <DTB size or 0>
  os_version     = 0
  name[16]       = "nuxel-s10plus"
  cmdline[512]   = <kernel cmdline>
  id[8]          = 0 (SHA-1 of all pages)
  extra_cmdline[1024] = ""
  padding to page_size, then:
  kernel_data (padded to page_size)
  ramdisk_data (padded to page_size)
  DTB data (optional, padded to page_size)

Key addresses for Exynos 9820 (from pmOS beyond2lte boot.img analysis):
  kernel_addr  = 0x80008000   # PLACEHOLDER — verify from real device boot.img
  ramdisk_addr = 0x84000000   # PLACEHOLDER — verify from real device boot.img
  tags_addr    = 0x80000100   # PLACEHOLDER — verify from real device boot.img
The defaults are used ONLY when --addresses-from-device is not given, and a
warning is printed. Never fabricate addresses: get the real ones from the
stock boot.img pulled off the physical device (Phase 0 inventory,
docs/s10plus-device-inventory.md).

Usage:
  python3 boot/s10plus/pack-boot-v1.sh \\
      --kernel kernel/s10plus/.build/out/arch/arm64/boot/Image.gz \\
      --ramdisk boot/initramfs/initramfs.cpio.gz \\
      --dtb kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dtb \\
      --cmdline "earlycon=exynos4210,0x10020000 console=ttySAC0,115200 nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw" \\
      --output /tmp/nuxel-beyond2lte-boot.img

  --addresses-from-device <stock-boot.img>   read kernel/ramdisk/tags load
      addresses from a stock v1 boot.img (uses tools/read-boot-header-v1.py).
  --kernel-addr <HEX>      kernel load address (overrides default/device file).
  --ramdisk-addr <HEX>     ramdisk load address (overrides default/device file).
  --tags-addr <HEX>        tags/DTB load address (overrides default/device file).
  -h, --help                                  show this help and exit.

Exit codes: 0 ok, 1 usage/input error, 2 cannot read input, 3 bad output.
"""

import argparse
import json
import os
import struct
import subprocess
import sys

MAGIC = b"ANDROID!"
PAGE_SIZE = 2048
HEADER_SIZE = 1632
# Real boot_img_hdr_v1 header size, written to the v1 `header_size` field when
# --v1-spec is used.  Mirrors this unit's TWRP recovery.img (0x18000171 = 12.0.0).
HEADER_SIZE_V1 = 1648
OS_VERSION_DEFAULT = 0x18000171
NAME = b"nuxel-s10plus"

# PLACEHOLDER — verify from real device boot.img (Phase 0 inventory).
DEFAULT_KERNEL_ADDR = 0x80008000
DEFAULT_RAMDISK_ADDR = 0x84000000
DEFAULT_TAGS_ADDR = 0x80000100

HDR_STRUCT = struct.Struct("<8s10I16s512s8I1024s")
assert HDR_STRUCT.size == HEADER_SIZE


def round_up(value, alignment):
    return ((value + alignment - 1) // alignment) * alignment


def read_file(path, what):
    if path == "/dev/null":
        return b""
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        sys.stderr.write(f"pack-boot-v1: cannot read {what} '{path}': {exc}\n")
        sys.exit(2)


def addresses_from_device(stock_img, script_dir):
    """Extract kernel/ramdisk/tags addresses from a stock v1 boot.img."""
    tool = os.path.join(script_dir, "..", "..", "tools", "read-boot-header-v1.py")
    proc = subprocess.run(
        [sys.executable, tool, "--json", stock_img],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(f"pack-boot-v1: cannot parse stock boot.img:\n{proc.stderr}")
        sys.exit(proc.returncode or 1)
    info = json.loads(proc.stdout)
    return (info["kernel_addr"], info["ramdisk_addr"], info["tags_addr"])


def pack(kernel, ramdisk, dtb, cmdline, output, kernel_addr, ramdisk_addr, tags_addr, v1_spec=False):
    kernel_data = read_file(kernel, "kernel")
    ramdisk_data = read_file(ramdisk, "ramdisk")
    dtb_data = read_file(dtb, "dtb") if dtb else b""

    # cmdline is a fixed 512-byte asciiz field
    cmdline_field = cmdline.encode("utf-8", "replace")[:511] + b"\x00"
    cmdline_field = cmdline_field.ljust(512, b"\x00")

    header = HDR_STRUCT.pack(
        MAGIC,
        len(kernel_data), kernel_addr & 0xFFFFFFFF,
        len(ramdisk_data), ramdisk_addr & 0xFFFFFFFF,
        0, 0,                              # second_size, second_addr
        tags_addr & 0xFFFFFFFF,
        PAGE_SIZE,
        # offset 40: real header v1 = `header_version`; the legacy (non-spec)
        # layout this tool shipped with put the DTB size here instead.
        (1 if v1_spec else len(dtb_data)),
        (OS_VERSION_DEFAULT if v1_spec else 0),   # offset 44: os_version
        NAME.ljust(16, b"\x00"),
        cmdline_field,
        *([0] * 8),                        # id
        b"".ljust(1024, b"\x00"),          # extra_cmdline
    )
    assert len(header) == HEADER_SIZE
    if v1_spec:
        # boot_img_hdr_v1 tail: recovery_dtbo_size=0, recovery_dtbo_offset=0,
        # header_size=1648.  Both dtbo fields stay zero because S-Boot builds
        # the device tree from the dtb partition + DTBO overlay on this unit.
        header += struct.pack("<IQI", 0, 0, HEADER_SIZE_V1)

    with open(output, "wb") as fh:
        fh.write(header.ljust(PAGE_SIZE, b"\x00"))
        fh.write(kernel_data.ljust(round_up(len(kernel_data), PAGE_SIZE), b"\x00"))
        fh.write(ramdisk_data.ljust(round_up(len(ramdisk_data), PAGE_SIZE), b"\x00"))
        if dtb_data:
            fh.write(dtb_data.ljust(round_up(len(dtb_data), PAGE_SIZE), b"\x00"))

    with open(output, "rb") as fh:
        first = fh.read(8)
    if first != MAGIC:
        sys.stderr.write("pack-boot-v1: internal error — output magic mismatch\n")
        sys.exit(3)

    print(f"pack-boot-v1: wrote {output}")
    print(f"  kernel_size={len(kernel_data)} kernel_addr=0x{kernel_addr:08x}")
    print(f"  ramdisk_size={len(ramdisk_data)} ramdisk_addr=0x{ramdisk_addr:08x}")
    print(f"  dt_size={len(dtb_data)} tags_addr=0x{tags_addr:08x} page_size={PAGE_SIZE}")
    if v1_spec:
        print(f"  header_version=1 os_version=0x{OS_VERSION_DEFAULT:08x} header_size={HEADER_SIZE_V1}")
    print(f"  name={NAME.decode()} cmdline='{cmdline}'")


def main(argv):
    parser = argparse.ArgumentParser(
        prog="pack-boot-v1.sh",
        description="Pack a legacy Android boot image (header v1, page 2048) for the S10+.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--kernel", help="path to the kernel image (Image.gz or u-boot.bin)")
    parser.add_argument("--ramdisk", help="path to the ramdisk (initramfs.cpio.gz; /dev/null = empty)")
    parser.add_argument("--dtb", default=None, help="optional DTB appended after the ramdisk")
    parser.add_argument("--cmdline", default="", help="kernel command line (<=511 bytes)")
    parser.add_argument("--output", help="output boot.img path")
    parser.add_argument("--kernel-addr", metavar="HEX", type=lambda v: int(v, 0),
                        help="kernel load address (e.g. 0x80008000); overrides the default")
    parser.add_argument("--ramdisk-addr", metavar="HEX", type=lambda v: int(v, 0),
                        help="ramdisk load address (e.g. 0x84000000); overrides the default")
    parser.add_argument("--tags-addr", metavar="HEX", type=lambda v: int(v, 0),
                        help="tags/DTB load address (e.g. 0x80000100); overrides the default")
    parser.add_argument("--addresses-from-device", metavar="STOCK_BOOT_IMG",
                        help="read kernel/ramdisk/tags load addresses from a stock v1 boot.img")
    parser.add_argument("--v1-spec", action="store_true",
                        help="write a spec-compliant boot_img_hdr_v1 (header_version=1 at "
                             "offset 40, os_version at 44, header_size=1648) instead of the "
                             "legacy layout that stored the DTB size at offset 40")
    args = parser.parse_args(argv)

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Explicit --kernel-addr/--ramdisk-addr/--tags-addr win over both the
    # stock-boot.img values and the placeholder defaults.
    kernel_addr = args.kernel_addr
    ramdisk_addr = args.ramdisk_addr
    tags_addr = args.tags_addr

    if args.addresses_from_device:
        dev_kernel, dev_ramdisk, dev_tags = addresses_from_device(args.addresses_from_device, script_dir)
        kernel_addr = kernel_addr if kernel_addr is not None else dev_kernel
        ramdisk_addr = ramdisk_addr if ramdisk_addr is not None else dev_ramdisk
        tags_addr = tags_addr if tags_addr is not None else dev_tags
        print(f"pack-boot-v1: addresses from {args.addresses_from_device}: "
              f"kernel=0x{kernel_addr:08x} ramdisk=0x{ramdisk_addr:08x} tags=0x{tags_addr:08x}")
    else:
        kernel_addr = kernel_addr if kernel_addr is not None else DEFAULT_KERNEL_ADDR
        ramdisk_addr = ramdisk_addr if ramdisk_addr is not None else DEFAULT_RAMDISK_ADDR
        tags_addr = tags_addr if tags_addr is not None else DEFAULT_TAGS_ADDR

    if (args.kernel_addr is None and args.ramdisk_addr is None
            and args.tags_addr is None and not args.addresses_from_device):
        print("pack-boot-v1: WARNING using PLACEHOLDER load addresses "
              f"(kernel=0x{kernel_addr:08x} ramdisk=0x{ramdisk_addr:08x} tags=0x{tags_addr:08x}).")
        print("pack-boot-v1: WARNING verify from the real device stock boot.img "
              "(Phase 0, docs/s10plus-device-inventory.md) before flashing.")
    elif args.kernel_addr is not None or args.ramdisk_addr is not None or args.tags_addr is not None:
        print(f"pack-boot-v1: load addresses (explicit): "
              f"kernel=0x{kernel_addr:08x} ramdisk=0x{ramdisk_addr:08x} tags=0x{tags_addr:08x}")

    if not args.kernel or not args.ramdisk or not args.output:
        parser.error("--kernel, --ramdisk and --output are required (--dtb optional).")

    pack(args.kernel, args.ramdisk, args.dtb, args.cmdline, args.output,
         kernel_addr, ramdisk_addr, tags_addr, v1_spec=args.v1_spec)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
