#!/usr/bin/env python3
"""Collect recursive DT_NEEDED closure for local target ELFs from same ADB device."""
import argparse
import os
import struct
import subprocess
import sys
from pathlib import Path

DIRS = [
    "/vendor/lib64", "/vendor/lib64/hw", "/vendor/lib64/vndk-29",
    "/vendor/lib64/vndk-sp-29", "/vendor/lib", "/vendor/lib/hw",
    "/system/lib64", "/system/lib64/vndk-29", "/system/lib64/vndk-sp-29",
    "/system/lib64/vndk", "/system/lib64/vndk-sp", "/system/lib",
    "/system/lib/hw", "/apex/com.android.runtime/lib64/bionic",
    "/apex/com.android.runtime/lib/bionic",
]
SEEDS = [
    "vendor/bin/hw/lhd", "vendor/bin/lhd",
    "vendor/lib64/sensors.sensorhub.so", "vendor/lib/sensors.sensorhub.so",
    "vendor/lib64/hw/sensors.exynos9820.so", "vendor/lib/hw/sensors.exynos9820.so",
]


def parse_elf(path):
    b = Path(path).read_bytes()
    if len(b) < 52 or b[:4] != b"\x7fELF":
        return None
    cls, data = b[4], b[5]
    endian = "<" if data == 1 else ">" if data == 2 else None
    if not endian or cls not in (1, 2):
        return None
    if cls == 2:
        machine = struct.unpack_from(endian + "H", b, 18)[0]
        phoff = struct.unpack_from(endian + "Q", b, 32)[0]
        phentsize, phnum = struct.unpack_from(endian + "HH", b, 54)
        phfmt, dynfmt = endian + "IIQQQQQQ", endian + "qQ"
        dynsize = 16
    else:
        machine = struct.unpack_from(endian + "H", b, 18)[0]
        phoff = struct.unpack_from(endian + "I", b, 28)[0]
        phentsize, phnum = struct.unpack_from(endian + "HH", b, 42)
        phfmt, dynfmt = endian + "IIIIIIII", endian + "iI"
        dynsize = 8
    loads, dynamic = [], None
    for i in range(phnum):
        off = phoff + i * phentsize
        if off + struct.calcsize(phfmt) > len(b):
            break
        p = struct.unpack_from(phfmt, b, off)
        p_type = p[0]
        if cls == 2:
            p_offset, p_vaddr, p_filesz = p[2], p[3], p[5]
        else:
            p_offset, p_vaddr, p_filesz = p[1], p[2], p[4]
        if p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))
        elif p_type == 2:
            dynamic = (p_offset, p_filesz)
    if not dynamic:
        return {"class": cls, "machine": machine, "needed": [], "soname": None}
    tags = []
    doff, dsize = dynamic
    for off in range(doff, min(doff + dsize, len(b)) - dynsize + 1, dynsize):
        tag, val = struct.unpack_from(dynfmt, b, off)
        if tag == 0:
            break
        tags.append((tag, val))
    strtab_va = next((v for t, v in tags if t == 5), None)
    if strtab_va is None:
        return {"class": cls, "machine": machine, "needed": [], "soname": None}
    strsz = next((v for t, v in tags if t == 10), 1 << 24)
    strtab_off = None
    for va, po, psz in loads:
        if va <= strtab_va < va + psz:
            strtab_off = po + (strtab_va - va)
            break
    if strtab_off is None:
        return {"class": cls, "machine": machine, "needed": [], "soname": None}
    strings = b[strtab_off:min(strtab_off + strsz, len(b))]
    def getstr(idx):
        if idx < 0 or idx >= len(strings):
            return None
        end = strings.find(b"\0", idx)
        if end < 0:
            return None
        return strings[idx:end].decode("utf-8", "replace")
    needed = [getstr(v) for t, v in tags if t == 1]
    soname = next((getstr(v) for t, v in tags if t == 14), None)
    return {"class": cls, "machine": machine, "needed": [x for x in needed if x], "soname": soname}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adb", default="adb")
    ap.add_argument("--serial", required=True)
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    root = Path(args.root)
    def adb(*cmd, check=False):
        return subprocess.run([args.adb, "-s", args.serial, *cmd], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, check=check)
    pulled = set()
    unresolved = set()
    queue = []
    for rel in SEEDS:
        p = root / rel
        if p.is_file(): queue.append(p)
    # Linker paths for 32/64-bit vendor executables.
    for remote in ("/system/bin/linker64", "/system/bin/linker"):
        if adb("shell", "test", "-r", remote).returncode == 0:
            dest = root / remote.lstrip("/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            r = adb("pull", remote, str(dest))
            if r.returncode == 0:
                pulled.add(remote)
                print("PULLED_INTERPRETER", remote)
    seen_local = set()
    while queue:
        local = queue.pop(0)
        if local in seen_local:
            continue
        seen_local.add(local)
        info = parse_elf(local)
        if not info:
            continue
        for lib in info["needed"]:
            already = list(root.rglob(lib))
            if already:
                queue.extend(p for p in already if p not in seen_local)
                continue
            found = None
            for d in DIRS:
                remote = d.rstrip("/") + "/" + lib
                if adb("shell", "test", "-r", remote).returncode == 0:
                    found = remote
                    break
            if not found:
                unresolved.add(lib)
                continue
            dest = root / found.lstrip("/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            r = adb("pull", found, str(dest))
            if r.returncode != 0:
                unresolved.add(lib)
                continue
            pulled.add(found)
            print("PULLED_DEP", found)
            queue.append(dest)
            if len(pulled) > 512:
                print("ABORT: dependency closure exceeded 512 files", file=sys.stderr)
                break
    report = root / "reports" / "elf-dependencies.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w") as f:
        for p in sorted(seen_local):
            info = parse_elf(p)
            if info:
                f.write(f"{p.relative_to(root)}: ELF{32 if info['class']==1 else 64} machine={info['machine']} soname={info['soname']}\n")
                for lib in info["needed"]:
                    f.write(f"  NEEDED {lib}\n")
        f.write("\nPULLED_REMOTE_LIBRARIES\n")
        for p in sorted(pulled): f.write(p + "\n")
        f.write("\nUNRESOLVED_NEEDED\n")
        for lib in sorted(unresolved): f.write(lib + "\n")
    print(f"ELF dependency scan complete: {len(seen_local)} local ELFs inspected, {len(pulled)} remote files pulled, {len(unresolved)} dependencies unresolved.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
