#!/usr/bin/env python3
"""build-qcdt-boot.py - rewrite the DTB region of a legacy Android boot image
(header v1, "ANDROID!") into a *lk2nd-compatible QCDT v3 table*.

Why: lk2nd (msm8916-mainline/lk2nd, msm8953 target) validates the boot image's
appended device-tree region with dev_tree_validate()/dev_tree_get_entry_info().
That code expects Qualcomm's "QCDT" table with lk2nd's OWN header layout:

    struct dt_table {                 /* DEV_TREE_HEADER_SIZE == 12 */
        u32 magic;                    /* 0x54444351  ("QCDT" bytes)      */
        u32 version;                  /* 3 (DEV_TREE_VERSION_V3)         */
        u32 num_entries;
    };
    /* entries start at offset 12, DEV_TREE_DT_ENTRY_SIZE_V3 == 40 bytes */
    struct dt_entry {                 /* on-disk layout used by lk2nd  */
        u32 platform_id;              /* qcom,msm-id[0]                */
        u32 variant_id;               /* hw platform / board variant   */
        u32 board_hw_subtype;
        u32 soc_rev;                  /* qcom,msm-id[1]                */
        u32 pmic_rev[4];              /* qcom,pmic-id (may be 0)       */
        u32 offset;                   /* dtb offset from table start   */
        u32 size;
    };

A raw FDT appended after the ramdisk (what mkbootimg --dtb produces, and what
the previous build had) makes lk2nd abort with "Bad magic in device tree table".
The table produced here matches the msm8953 target's identity as printed by
lk2nd on the device:
    board_platform_id() = 349 (0x15d)   board_soc_version() = 0x00010000
    board_target_id()   = 0x10008       board_hardware_subtype() = 0
=> msm-id = 0x15d, hw id low byte = 0x08, subtype low byte = 0.
Because we cannot read SMEM offline, we emit a small *matrix* of entries that
all point at the same DTB, covering the plausible hw-id and HLOS/DDR subtype
encodings, so platform_dt_absolute_match() succeeds. Only the DTB region is
touched; kernel, ramdisk and cmdline are copied byte-for-byte.

Usage:
  python3 tools/build-qcdt-boot.py <in_boot.img> <out_boot.img> [--combined lk2nd.img <out.img>]

Exit: 0 ok, 1 usage, 2 read error, 3 bad input image.
"""
import struct, sys, os

MAGIC = b"ANDROID!"
PAGE = 2048
HDR_SIZE = 1632
QCDT_MAGIC = 0x54444351          # b"QCDT"
QCDT_HDR = 12                    # DEV_TREE_HEADER_SIZE
ENT_V3 = 40                      # DEV_TREE_DT_ENTRY_SIZE_V3
MSM_ID = 0x15d                   # QCOM_ID_SDM632/msm8953-family for ocean
HW_LOW = 0x08                    # board_hardware_id() & 0xff  (from on-device log)
SOC_REV = 0
PMIC = (0, 0, 0, 0)


def round_up(n, a=PAGE):
    return ((n + a - 1) // a) * a


def parse_hdr(d):
    if d[:8] != MAGIC:
        raise ValueError("not an ANDROID! image")
    f = struct.unpack_from("<10I", d, 8)
    return {"kernel_size": f[0], "kernel_addr": f[1], "ramdisk_size": f[2],
            "ramdisk_addr": f[3], "second_size": f[4], "second_addr": f[5],
            "tags_addr": f[6], "page_size": f[7], "dt_size": f[8], "os_version": f[9]}


def read_fdt(dtb):
    magic, total = struct.unpack_from(">2I", dtb, 0)
    if magic != 0xd00dfeed:
        raise ValueError("dtb magic 0x%08x != 0xd00dfeed" % magic)
    return total


def build_table(dtb, variant_ids, subtypes):
    off = QCDT_HDR + ENT_V3 * len(variant_ids) * len(subtypes)
    dtb_off = round_up(off, 4)
    entries = []
    for v in variant_ids:
        for s in subtypes:
            entries.append(struct.pack("<10I", MSM_ID, v, s, SOC_REV,
                                       PMIC[0], PMIC[1], PMIC[2], PMIC[3],
                                       dtb_off, len(dtb)))
    table = struct.pack("<3I", QCDT_MAGIC, 3, len(entries)) + b"".join(entries)
    table = table.ljust(dtb_off, b"\x00") + dtb
    return table, dtb_off


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 1
    src, dst = argv[0], argv[1]
    combined = None
    if len(argv) >= 5 and argv[2] == "--combined":
        combined = (argv[3], argv[4])
    with open(src, "rb") as f:
        data = bytearray(f.read())
    h = parse_hdr(data)
    if h["page_size"] != PAGE:
        print("unexpected page_size", h["page_size"], file=sys.stderr); return 3
    koff = PAGE
    roff = round_up(koff + h["kernel_size"])
    doff = round_up(roff + h["ramdisk_size"])
    if h["dt_size"] <= 1:
        print("input image has no DTB to wrap", file=sys.stderr); return 3
    dtb = bytes(data[doff:doff + h["dt_size"]])
    total_dtb = read_fdt(dtb)
    dtb = dtb[:total_dtb]

    variant_ids = [0x008 + 0x100 * i for i in range(17)]   # ..0x1008
    subtypes = [0x100 * i for i in range(8)]               # 0x000..0x700
    table, dtb_off = build_table(dtb, variant_ids, subtypes)

    out = bytearray(data[:doff])            # header + kernel + ramdisk (verbatim)
    out += table
    out += b"\x00" * (round_up(len(out)) - len(out))
    struct.pack_into("<I", out, 8 + 8 * 4, len(table))     # dt_size field
    if dtb_off + len(dtb) > len(table):
        print("internal: dtb overflow", file=sys.stderr); return 3
    with open(dst, "wb") as f:
        f.write(out)
    print(f"wrote {dst} ({len(out)} bytes)")
    print(f"  dtb={len(dtb)}B  qcdt entries={len(variant_ids)*len(subtypes)}"
          f"  table={len(table)}B  dtb@table+{dtb_off}  dt_size={len(table)}")

    if combined:
        lk2, comb = combined
        with open(lk2, "rb") as f:
            lk = f.read()
        lk_pad = lk.ljust(512 * 1024, b"\x00")
        if len(lk_pad) != 512 * 1024:
            print("lk2nd.img larger than 512 KiB", file=sys.stderr); return 3
        with open(comb, "wb") as f:
            f.write(lk_pad); f.write(out)
        print(f"wrote {comb} ({len(lk_pad)+len(out)} bytes) = lk2nd@0 + boot@{512*1024}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
