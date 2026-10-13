#!/usr/bin/env python3
"""read-boot-header-v1.py — parse a legacy Android boot image (header v1).

Reads a stock boot.img (header version 1, page_size 2048, "ANDROID!" magic),
validates the magic and page size, and prints the fields the S10+ Phase 0
operator needs to fill KERNEL_ADDR / RAMDISK_ADDR / TAGS_ADDR, plus every
other header field (kernel_size, ramdisk_size, dt_size, os_version, name,
id, cmdline, extra_cmdline).

This tool NEVER fabricates values: it only prints what the header contains.
If a field is absent/zero, it prints it as-is (0). Load addresses must be
verified against the real stock boot.img pulled from the physical device —
do not copy them from any other source.

Usage:
  python3 tools/read-boot-header-v1.py <stock-boot.img> [--json]

Options:
  -h, --help   show this help and exit (runs offline, no file required)
  --json       emit a single JSON object for machine consumption (used by
               boot/s10plus/pack-boot-v1.sh --addresses-from-device)

Exit codes:
  0  parsed successfully
  1  usage error
  2  cannot read the input file
  3  not a valid v1 boot image (bad magic, truncated header, or bad page_size)
"""

import json
import struct
import sys

MAGIC = b"ANDROID!"
HEADER_SIZE = 1632  # bytes of struct boot_img_hdr_v1 (before page padding)

# struct boot_img_hdr_v1 (little-endian), see AOSP system/tools/mkbootimg:
#   uint8_t  magic[8];
#   uint32_t kernel_size; kernel_addr; ramdisk_size; ramdisk_addr;
#   uint32_t second_size; second_addr; tags_addr; page_size;
#   uint32_t dt_size; os_version;
#   uint8_t  name[16]; cmdline[512];
#   uint32_t id[8];
#   uint8_t  extra_cmdline[1024];
HDR_STRUCT = struct.Struct("<8s10I16s512s8I1024s")
assert HDR_STRUCT.size == HEADER_SIZE, HDR_STRUCT.size


def round_up(value, alignment):
    """Round value up to the next multiple of alignment."""
    return ((value + alignment - 1) // alignment) * alignment


def decode_os_version(raw):
    """Decode the v1 os_version uint32 into (a.b.c, security_patch_level).

    Bit layout (AOSP bootimg.h / mkbootimg.py): bits 31-25 = major,
    24-18 = minor, 17-11 = patch, bits 10-4 = (year - 2000), bits 3-0 =
    month; os_patch_level is encoded as ((year - 2000) << 4) | month.
    Returns (version_str, spl_str_or_None). Never invents values — if the
    encoding is not meaningful, returns the raw number as a string.
    """
    major = (raw >> 25) & 0x7F
    minor = (raw >> 18) & 0x7F
    patch = (raw >> 11) & 0x7F
    spl = raw & 0x7FF
    version = f"{major}.{minor}.{patch}"
    year_offset = (spl >> 4) & 0x7F
    month = spl & 0xF
    if 0 <= year_offset < 128 and 1 <= month <= 12:
        return version, f"{2000 + year_offset:04d}-{month:02d}"
    return version, str(spl)


def parse_boot_img(path):
    """Parse a v1 boot.img; return a dict of header fields + data offsets."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        sys.stderr.write(f"read-boot-header-v1: cannot read '{path}': {exc}\n")
        sys.exit(2)

    if len(data) < HEADER_SIZE:
        sys.stderr.write(
            f"read-boot-header-v1: '{path}' is too small to hold a v1 header "
            f"({len(data)} < {HEADER_SIZE} bytes)\n"
        )
        sys.exit(3)

    fields = HDR_STRUCT.unpack_from(data, 0)
    magic = fields[0]
    if magic != MAGIC:
        sys.stderr.write(
            f"read-boot-header-v1: bad magic {magic!r} (expected {MAGIC!r}) "
            f"in '{path}' — not a legacy Android boot image\n"
        )
        sys.exit(3)

    # struct.unpack flattens repeated counts ("10I", "8I"), so the layout is:
    #   0 magic | 1..10 kernel_size..os_version | 11 name | 12 cmdline
    #   13..20 id (8 x uint32) | 21 extra_cmdline
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr = fields[1:5]
    second_size, second_addr, tags_addr, page_size = fields[5:9]
    dt_size, os_version = fields[9:11]
    name = fields[11].split(b"\x00", 1)[0].decode("ascii", "replace")
    cmdline = fields[12].split(b"\x00", 1)[0].decode("utf-8", "replace")
    raw_id = fields[13:21]
    extra_cmdline = fields[21].split(b"\x00", 1)[0].decode("utf-8", "replace")

    if page_size == 0:
        sys.stderr.write(
            f"read-boot-header-v1: '{path}' declares page_size=0 — invalid\n"
        )
        sys.exit(3)
    if page_size != 2048:
        sys.stderr.write(
            f"read-boot-header-v1: '{path}' declares page_size={page_size} — "
            f"expected 2048 for the S10+ (beyond2lte) stock boot image\n"
        )
        sys.exit(3)

    kernel_offset = page_size
    ramdisk_offset = page_size + round_up(kernel_size, page_size)
    second_offset = ramdisk_offset + round_up(ramdisk_size, page_size)
    dt_offset = second_offset + round_up(second_size, page_size)

    os_version_str, os_spl = decode_os_version(os_version)

    return {
        "path": path,
        "magic": magic.decode("ascii", "replace"),
        "kernel_size": kernel_size,
        "kernel_addr": kernel_addr,
        "kernel_addr_hex": hex(kernel_addr),
        "ramdisk_size": ramdisk_size,
        "ramdisk_addr": ramdisk_addr,
        "ramdisk_addr_hex": hex(ramdisk_addr),
        "second_size": second_size,
        "second_addr": second_addr,
        "second_addr_hex": hex(second_addr),
        "tags_addr": tags_addr,
        "tags_addr_hex": hex(tags_addr),
        "page_size": page_size,
        "dt_size": dt_size,
        "os_version": os_version,
        "os_version_str": os_version_str,
        "os_security_patch_level": os_spl,
        "name": name,
        "cmdline": cmdline,
        "id": "".join(f"{v:08x}" for v in raw_id),
        "extra_cmdline": extra_cmdline,
        "kernel_offset": kernel_offset,
        "ramdisk_offset": ramdisk_offset,
        "second_offset": second_offset,
        "dt_offset": dt_offset,
    }


def print_human(info):
    """Print the parsed fields in a human-readable, copy-pasteable form."""
    w = sys.stdout.write
    w(f"# {info['path']}\n")
    w(f"magic:              {info['magic']}\n")
    w(f"kernel_size:        {info['kernel_size']} bytes\n")
    w(f"kernel_addr:        {info['kernel_addr_hex']}\n")
    w(f"ramdisk_size:       {info['ramdisk_size']} bytes\n")
    w(f"ramdisk_addr:       {info['ramdisk_addr_hex']}\n")
    w(f"second_size:        {info['second_size']} bytes\n")
    w(f"second_addr:        {info['second_addr_hex']}\n")
    w(f"tags_addr:          {info['tags_addr_hex']}\n")
    w(f"page_size:          {info['page_size']}\n")
    w(f"dt_size:            {info['dt_size']} bytes\n")
    w(f"os_version:         {info['os_version']} "
      f"(decoded: {info['os_version_str']}, "
      f"spl: {info['os_security_patch_level'] or 'n/a'})\n")
    w(f"name:               {info['name']}\n")
    w(f"cmdline:            {info['cmdline']}\n")
    w(f"id:                 {info['id']}\n")
    w(f"extra_cmdline:      {info['extra_cmdline']}\n")
    w(f"kernel_offset:      {info['kernel_offset']}\n")
    w(f"ramdisk_offset:     {info['ramdisk_offset']}\n")
    w(f"second_offset:      {info['second_offset']}\n")
    w(f"dt_offset:          {info['dt_offset']}\n")
    w("\n# Fill these into docs/s10plus-device-inventory.md:\n")
    w(f"KERNEL_ADDR:        {info['kernel_addr_hex']}\n")
    w(f"RAMDISK_ADDR:       {info['ramdisk_addr_hex']}\n")
    w(f"TAGS_ADDR:          {info['tags_addr_hex']}\n")


def main(argv):
    json_out = False
    paths = []
    for arg in argv:
        if arg in ("-h", "--help"):
            sys.stdout.write(__doc__)
            return 0
        if arg == "--json":
            json_out = True
            continue
        if arg.startswith("-"):
            sys.stderr.write(f"read-boot-header-v1: unknown option '{arg}'\n")
            sys.stderr.write("Try 'python3 tools/read-boot-header-v1.py --help'.\n")
            return 1
        paths.append(arg)

    if not paths:
        sys.stderr.write("read-boot-header-v1: missing boot.img path\n")
        sys.stderr.write("Try 'python3 tools/read-boot-header-v1.py --help'.\n")
        return 1

    info = parse_boot_img(paths[0])
    if json_out:
        json.dump(info, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print_human(info)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
