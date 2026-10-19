#!/usr/bin/env python3
"""patch-boot-cmdline.py — replace the kernel cmdline of a legacy Android boot
image (header v1, "ANDROID!") in place-safe fashion.

Reads <in.img>, writes <out.img> with the 512-byte cmdline field replaced by the
new cmdline (NUL-padded).  Every other byte of the image is copied verbatim —
this is a reversible, byte-level edit of one fixed header field, nothing else.

Usage:
  python3 tools/patch-boot-cmdline.py <in.img> <out.img> "<new cmdline>"

Exit codes: 0 ok, 1 usage, 2 cannot read, 3 not a valid v1 boot image.
"""
import struct
import sys

MAGIC = b"ANDROID!"
HEADER_FORMAT = "<8s10I16s512s32s1024s"   # struct boot_img_hdr_v1
CMDLINE_OFFSET = 8 + 10 * 4 + 16          # magic + 10 u32 (through os_version) + name[16]
CMDLINE_LEN = 512


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 1
    src, dst, new_cmdline = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        with open(src, "rb") as f:
            data = bytearray(f.read())
    except OSError as e:
        print(f"cannot read {src}: {e}", file=sys.stderr)
        return 2

    if len(data) < 1632 or bytes(data[:8]) != MAGIC:
        print(f"{src}: not a legacy Android boot image (bad magic)", file=sys.stderr)
        return 3

    (page_size,) = struct.unpack_from("<I", data, 8 + 7 * 4)  # page_size is u32 #8
    if page_size == 0 or page_size & (page_size - 1):
        print(f"{src}: invalid page_size {page_size}", file=sys.stderr)
        return 3

    old = bytes(data[CMDLINE_OFFSET:CMDLINE_OFFSET + CMDLINE_LEN]).split(b"\0")[0]
    enc = new_cmdline.encode()
    if len(enc) > CMDLINE_LEN:
        print(f"cmdline too long ({len(enc)} > {CMDLINE_LEN})", file=sys.stderr)
        return 1
    data[CMDLINE_OFFSET:CMDLINE_OFFSET + CMDLINE_LEN] = enc.ljust(CMDLINE_LEN, b"\0")

    with open(dst, "wb") as f:
        f.write(data)

    print(f"old cmdline: {old.decode(errors='replace')}")
    print(f"new cmdline: {new_cmdline}")
    print(f"wrote {dst} ({len(data)} bytes, page_size {page_size})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
