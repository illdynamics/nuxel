#!/usr/bin/env python3
"""
Build a structurally-correct Samsung S10+ (beyond2lte) DTBO partition image.

The DTBO partition (sda13 / dtbo.img, 8,388,608 bytes) uses the standard AOSP
dt_table format (magic 0xd7b7ab1e, big-endian), which S-Boot parses to select
one board overlay by hw_rev. Each entry is an AOSP tree whose top-level
properties are:

    dtbo-hw_rev      = the minimum hardware revision this overlay applies to
    dtbo-hw_rev_end  = the maximum (0xff = open-ended)

This device boots with `androidboot.revision=26` (/ `androidboot.dtbo_idx=9`),
so S-Boot selects the entry whose hw_rev range covers 26: the
`exynos9820-beyond2lte_eur_open_26.dtbo` overlay (dtbo-hw_rev = <0x1a>).

ENTRY ORDER (authoritative, from arch/arm64/boot/dts/Makefile, dtbo-y list
for beyond2lte_eur_open, in index order 0..9):
    16, 17, 19, 23, 26, 18, 24, 04, 20, 25

IMPORTANT SAFETY NOTE: the `id`/`rev`/`custom[0..3]` fields of each dt_table
entry carry Samsung board/hw_rev metadata. The byte-exact values for THIS
physical unit must come from a known-good dump of sda13 or the stock SM-G975F
dtbo.img. This script sets structurally-sane defaults but MUST be verified
against the device before flashing; do not flash a guessed DTBO silently.
"""
import struct, sys, os

MAGIC = 0xd7b7ab1e
PAGE  = 2048  # S10+ reported page size for this partition

# The device's DTBO partition holds ONLY the 10 beyond2lte overlays, sorted by
# hw_rev ascending, so the active entry for hw_rev=26 lands at dtbo_idx=9:
#   [04, 16, 17, 18, 19, 20, 23, 24, 25, 26]  ->  index 9 = 26
# This matches `androidboot.revision=26` + `androidboot.dtbo_idx=9` AND the
# CAMERA_IMPLEMENTATION_LOG's "entry[9]=beyond2lte_26" (read from live sda13).
REVS = [4, 16, 17, 18, 19, 20, 23, 24, 25, 26]
# filenames are zero-padded two-digit (04 not 4)
SRC_DIR = os.path.join("/Users/wicked/x/nuxel", "kernel", "s10plus", ".build", "out", "arch", "arm64", "boot", "dts", "samsung")

def load_overlays():
    entries = []
    for i, rev in enumerate(REVS):
        fn = os.path.join(SRC_DIR, f"exynos9820-beyond2lte_eur_open_{rev:02d}.dtbo")
        if not os.path.isfile(fn):
            sys.exit(f"missing overlay: {fn}")
        data = open(fn, "rb").read()
        # hw_rev for this overlay = rev (0x1a for 26). rev field = 0 (AOSP)
        entries.append((data, rev, i))
    return entries

def build():
    entries = load_overlays()
    n = len(entries)
    header_size = 32
    entry_size  = 32
    cur = header_size + entry_size * n
    table = []
    for data, rev, idx in entries:
        cur = (cur + 3) & ~3
        off = cur
        # id: 0; rev: 0; custom[0..3]: encode (board_rev=rev, idx) for traceability
        #   AOSP/Samsung: custom fields are opaque to libufdt; S-Boot matches on
        #   the overlay's dtbo-hw_rev property, not these fields.
        table.append((len(data), off, 0, 0, rev, idx, 0, 0))
        cur += len(data)
        cur = (cur + 3) & ~3
    total = (cur + PAGE - 1) // PAGE * PAGE
    out = bytearray(total)
    struct.pack_into(">I", out, 0, MAGIC)
    struct.pack_into(">IIIIIII", out, 4, total, header_size, entry_size, n, header_size, PAGE, 0)
    for i, (size, off, id_, rev, c0, c1, c2, c3) in enumerate(table):
        struct.pack_into(">IIIIIIII", out, header_size + i*entry_size, size, off, id_, rev, c0, c1, c2, c3)
    for (size, off, *_rest), (data, *_r) in zip(table, entries):
        out[off:off+size] = data
    return out, table, total

def main():
    out, table, total = build()
    fn = "dtbo-sda13.img"
    open(fn, "wb").write(out)
    print(f"wrote {fn} ({total} bytes)")
    print(f"  magic=0x{MAGIC:08x} entries={len(table)}")
    for i, (size, off, id_, rev, c0, c1, c2, c3) in enumerate(table):
        print(f"  [{i}] size={size} off=0x{off:x} custom0(hw_rev)={c0} custom1(idx)={c1}")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()
