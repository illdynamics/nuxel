#!/usr/bin/env python3
"""
resolve_ipc41_vocab.py — reproducible recovery of the S5000AP IpcProtocol41
telephony command vocabulary from an owner-authorized vendor libsec-ril.so.

SPDX-License-Identifier: GPL-2.0-only

OFFLINE analysis tooling. Reads a lawfully-obtained vendor ELF (exact
SM-G975F / EFUJ2 pairing) and prints, WITHOUT transmitting anything or
executing vendor code, the complete (main_cmd) name map and the
(main_cmd, sub_cmd) name map recovered from:

  IpcProtocol41::GetMainCommandName(int) @0x323860
      byte jump-table @VA 0x149934 (base adr 0x32388c), 128 entries
  IpcProtocol41::GetSubCommandName(int,int) @0x323a58
      half jump-table @VA 0x1499b4 (base adr 0x323a8c), 128 entries
      per-family blocks resolve `adrp x9 + add x9` -> const char* tables in
      .data.rel.ro, whose pointer slots are filled at load time by
      R_AARCH64_RELATIVE relocations pointing at .rodata name strings.

Usage:
  python3 resolve_ipc41_vocab.py /path/to/libsec-ril.so

Expected vendor reference (SM-G975F, EFUJ2):
  GNU Build ID 60889dd714394ae0db7c2ecc2bf2740f
  sha256       b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3

No binary contents are printed; only recovered NAME strings.
"""
import struct, subprocess, re, sys, json

def main(path):
    data = open(path, "rb").read()
    out = subprocess.run(["strings", "-t", "x", path], capture_output=True, text=True).stdout
    va2str = {}
    for l in out.splitlines():
        m = re.match(r"^\s*([0-9a-f]+)\s+(.*)$", l)
        if m:
            va2str[int(m.group(1), 16)] = m.group(2)
    out2 = subprocess.run(["readelf", "-r", path], capture_output=True, text=True).stdout
    rel = {}
    for l in out2.splitlines():
        m = re.match(r"^\s*([0-9a-f]+)\s+[0-9a-f]+\s+R_AARCH64_RELATIV\s+([0-9a-f]+)\s*$", l)
        if m:
            rel[int(m.group(1), 16)] = int(m.group(2), 16) & 0xffffffff
    out3 = subprocess.run(["readelf", "-SW", path], capture_output=True, text=True).stdout
    sects = {}
    for l in out3.splitlines():
        m = re.match(r"^\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s*$", l)
        if m:
            sects[m.group(1)] = (int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16))
    def va2off(va):
        for nm, (addr, off, size) in sects.items():
            if addr <= va < addr + size and size > 0:
                return va - addr + off
        return None

    jt_main = 0x149934
    base_main = 0x32388c
    main_names = {}
    for i in range(128):
        o = va2off(jt_main + i)
        if o is None:
            continue
        b = data[o]
        main_names[i + 1] = base_main + b * 4
    out4 = subprocess.run(["objdump", "-d", "--start-address=0x323860",
                           "--stop-address=0x323a60", path],
                          capture_output=True, text=True).stdout
    block_str = {}
    lines = out4.splitlines()
    for idx, l in enumerate(lines):
        m = re.match(r"^([0-9a-f]+):\s+[0-9a-f]+\s+adrp\s+x0,\s*([0-9a-f]+)", l)
        if not m:
            continue
        pc, page = int(m.group(1), 16), int(m.group(2), 16)
        for j in range(idx + 1, min(idx + 3, len(lines))):
            m2 = re.search(r"add\s+x0,\s*x0,\s*#(?:0x)?([0-9a-f]+)", lines[j])
            if m2:
                va = page + int(m2.group(1), 16)
                block_str[pc] = va2str.get(va, "")
                break
    outmain = {main: block_str.get(target, "?") for main, target in main_names.items()}

    jt_sub = 0x1499b4
    base_sub = 0x323a8c
    blocks = {}
    for i in range(128):
        o = va2off(jt_sub + i * 2)
        if o is None:
            continue
        u16 = struct.unpack_from("<H", data, o)[0]
        blocks[i + 1] = base_sub + u16 * 4
    out5 = subprocess.run(["objdump", "-d", "--start-address=0x323a58",
                           "--stop-address=0x324660", path],
                          capture_output=True, text=True).stdout
    instr = []
    for l in out5.splitlines():
        m = re.match(r"^([0-9a-f]+):\s+[0-9a-f]+\s+(.*)$", l)
        if m:
            instr.append((int(m.group(1), 16), m.group(2)))
    table_info = {}
    for idx, (pc, txt) in enumerate(instr):
        if not ("ldr" in txt and "x0" in txt and "x9" in txt and "w8" in txt):
            continue
        page, add_va = None, None
        for j in range(idx - 1, max(-1, idx - 8), -1):
            tj = instr[j][1]
            m = re.search(r"adrp\s+x9,\s*([0-9a-f]+)", tj)
            if m:
                page = int(m.group(1), 16)
            m2 = re.search(r"add\s+x9,\s*x9,\s*#(?:0x)?([0-9a-f]+)", tj)
            if m2:
                add_va = int(m2.group(1), 16)
                break
        cnt = None
        for j in range(idx - 1, max(-1, idx - 12), -1):
            m3 = re.search(r"cmp\s+w8,\s*#0x([0-9a-f]+)", instr[j][1])
            if m3:
                cnt = int(m3.group(1), 16)
                break
        if page is not None and add_va is not None:
            table_info[pc] = (page + add_va, cnt)
    result = {}
    for main in sorted(blocks):
        blk = blocks[main]
        found = None
        for pc in sorted(table_info):
            if pc >= blk:
                found = table_info[pc]
                break
        result[main] = found
    outsub = {}
    for main, info in result.items():
        if not info:
            continue
        tbl, cnt = info
        names = []
        for i in range(cnt if cnt else 8):
            slot = tbl + i * 8
            val = rel.get(slot)
            names.append(va2str.get(val, "?") if val else "?")
        outsub[str(main)] = names
    print(json.dumps({"main_names": {str(k): v for k, v in outmain.items()},
                      "sub_names": outsub}, indent=1))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: resolve_ipc41_vocab.py <libsec-ril.so>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
