#!/usr/bin/env python3
"""Build-time regression gate: reject a beyond2lte BOOT image whose appended
device tree is missing the Shannon S5000AP modem io-device subtree.

Required modem io-devices (from exynos9820-beyond2lte_eur_open_26 DTBO):
  io_device_1  umts_ipc0  id 0xeb  (FMT)
  io_device_2  umts_ipc1  id 0xec
  io_device_3  umts_rfs0  id 0xf5  (RFS)
  io_device_20 umts_boot0 id 0xd7  (BOOT)
  rmnet0..7   (PDP data path; 8 entries)
  mif,num_iodevs == 0x16 (22)

The historical beyond2lte boot regression shipped a 9,394,176-byte zero-filled
appended DTB (SHA-256 a46939ac...). This gate fails that image and any image
missing the modem subtree, so future builds cannot silently remove the nodes.

Usage:
  tools/s10plus/check-modem-dt.py <boot.img>
Exit 0 = PASS (modem subtree present), 1 = FAIL, 2 = usage/input error.
"""
import struct, sys, os

FDT_MAGIC = 0xD00DFEED

def fail(msg):
    sys.stderr.write("check-modem-dt: FAIL: %s\n" % msg)
    sys.exit(1)

def unpack_dtb_from_boot(path):
    d = open(path, "rb").read()
    if d[:8] != b"ANDROID!":
        fail("not an Android boot image (no ANDROID! magic)")
    kernel_size, _, ramdisk_size = struct.unpack_from("<III", d, 8), struct.unpack_from("<III", d, 16), None
    # kernel_size at 8, ramdisk_size at 16 (after kernel_addr 12, ramdisk_addr 20)
    ks = struct.unpack_from("<I", d, 8)[0]
    rs = struct.unpack_from("<I", d, 16)[0]
    ps = struct.unpack_from("<I", d, 36)[0]
    def up(v, a=ps):
        return ((v + a - 1)//a)*a
    dtb_off = 2048 + up(ks) + up(rs)
    # dtb may be padded; read enough for header
    if dtb_off + 4 > len(d):
        fail("boot image truncated: no appended DTB region")
    return d[dtb_off:]

def parse_fdt_names(dtb):
    """Return (props_by_node, list_of_node_names) by walking FDT structure."""
    if len(dtb) < 40 or struct.unpack_from(">I", dtb, 0)[0] != FDT_MAGIC:
        fail("appended DTB has no FDT magic (zero-filled/truncated DTB)")
    total, off_struct, off_strings = struct.unpack_from(">III", dtb, 4)
    if total > len(dtb) or off_struct >= total or off_strings >= total:
        fail("appended DTB has invalid header offsets")
    def s(off):
        e = dtb.find(b"\x00", off)
        return dtb[off:e].decode("ascii", "replace") if e >= 0 else ""
    props = {}
    pos = off_struct
    node_names = []
    depth = 0
    while pos < total:
        tok = struct.unpack_from(">I", dtb, pos)[0]
        pos += 4
        if tok == 1:  # FDT_BEGIN_NODE
            name = s(pos)
            node_names.append(name)
            pos = (pos + len(name.encode()) + 1 + 3) & ~3
        elif tok == 2:  # FDT_END_NODE
            pass
        elif tok == 3:  # FDT_PROP
            nlen, nameoff = struct.unpack_from(">II", dtb, pos)
            pos += 8
            name = s(off_strings + nameoff)
            val = dtb[pos:pos+nlen]
            pos = (pos + nlen + 3) & ~3
            props.setdefault(name, []).append(val)
        elif tok == 9:  # FDT_END
            break
        else:
            fail("appended DTB: unknown FDT token 0x%x at 0x%x" % (tok, pos))
    return props, node_names

def be32(val):
    return int.from_bytes(val[:4], "big") if len(val) >= 4 else None

def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: check-modem-dt.py <boot.img>\n"); sys.exit(2)
    boot = sys.argv[1]
    if not os.path.isfile(boot):
        sys.stderr.write("check-modem-dt: missing image %s\n" % boot); sys.exit(2)
    dtb = unpack_dtb_from_boot(boot)
    props, node_names = parse_fdt_names(dtb)

    # num_iodevs must be 0x16 (22)
    num = be32(props.get("mif,num_iodevs", [b""])[0])
    if num != 0x16:
        fail("mif,num_iodevs=%s (want 0x16/22) — modem tree stripped" % (num,))

    # Collect all iod,name + iod,id pairs in order
    names = [v.decode("ascii", "replace").rstrip("\x00") for v in props.get("iod,name", [])]
    ids = [be32(v) for v in props.get("iod,id", [])]
    pairs = list(zip(names, ids))

    required = {
        "umts_ipc0": 0xeb,
        "umts_ipc1": 0xec,
        "umts_rfs0": 0xf5,
        "umts_boot0": 0xd7,
    }
    found = {n: i for n, i in pairs}
    for n, expect_id in required.items():
        if n not in found:
            fail("required io-device missing: %s (id 0x%x)" % (n, expect_id))
        if found[n] != expect_id:
            fail("io-device %s id=0x%x (want 0x%x)" % (n, found[n], expect_id))

    rmnet = [n for n, _ in pairs if n.startswith("rmnet")]
    if len(rmnet) != 8:
        fail("expected 8 rmnet* io-devices, found %d" % len(rmnet))

    total_io = sum(1 for n, _ in pairs if n.startswith(("umts_", "rmnet", "multipdp", "ipc_", "smd")))
    if len(pairs) != 22 and total_io < 22:
        fail("io-device child count=%d (want 22): %s" % (len(pairs), [n for n, _ in pairs]))

    print("check-modem-dt: PASS — num_iodevs=22, umts_ipc0=0xeb, umts_rfs0=0xf5, "
          "umts_boot0=0xd7, rmnet0..7 present (%d io-devices)" % len(pairs))
    return 0

if __name__ == "__main__":
    sys.exit(main())
