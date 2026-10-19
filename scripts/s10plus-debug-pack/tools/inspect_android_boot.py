#!/usr/bin/env python3
"""Offline legacy Android boot.img inspector; no writes to the image.
Handles Samsung's v0-style header (dt_size at offset 40). Builds a report,
extracts candidate valid flattened DTBs to the HOST output folder, and
lists files in gzip-compressed newc initramfs when present.
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import struct
import subprocess
import shutil
import sys

MAGIC = b"ANDROID!"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"

def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]

def align(n, page):
    return ((n + page - 1) // page) * page

def short_str(buf):
    return buf.split(b"\x00", 1)[0].decode("utf-8", errors="replace")

def read_newc_entries(data, cap=100000):
    """Validate newc headers; return entries and a few boot-critical payloads."""
    entries = []
    interesting = {}
    pos = 0
    for _ in range(cap):
        if pos + 110 > len(data):
            break
        header = data[pos:pos + 110]
        if header[:6] not in (b"070701", b"070702"):
            break
        try:
            values = [int(header[i:i + 8], 16) for i in range(6, 110, 8)]
        except ValueError:
            break
        size, namesize = values[6], values[11]
        mode = values[1]
        if not 1 <= namesize <= 4096 or pos + 110 + namesize > len(data):
            break
        name = data[pos + 110:pos + 110 + namesize].rstrip(b"\x00").decode("utf-8", "replace")
        payload_at = align(pos + 110 + namesize, 4)
        next_pos = align(payload_at + size, 4)
        if next_pos > len(data):
            break
        if name == "TRAILER!!!":
            break
        if name:
            entries.append({"name": name, "mode": oct(mode), "size": size})
            if name.lstrip("./") in ("init", "bin/sh", "etc/fstab", "etc/init", "etc/rc") and size <= 256 * 1024:
                interesting[name.lstrip("./")] = data[payload_at:payload_at + size]
        pos = next_pos
    return entries, interesting

def inspect(path, out):
    out.mkdir(parents=True, exist_ok=True)
    data = path.read_bytes()
    if len(data) < 2048 or data[:8] != MAGIC:
        raise ValueError("Not an Android boot image (missing ANDROID! magic)")
    kernel_size = u32(data, 8)
    ramdisk_size = u32(data, 16)
    second_size = u32(data, 24)
    page_size = u32(data, 36)
    dt_size = u32(data, 40)
    if page_size not in (2048, 4096, 8192, 16384):
        raise ValueError(f"Unexpected header page size {page_size}")
    kernel_at = page_size
    ramdisk_at = kernel_at + align(kernel_size, page_size)
    second_at = ramdisk_at + align(ramdisk_size, page_size)
    dt_at = second_at + align(second_size, page_size)
    if dt_at + dt_size > len(data):
        raise ValueError("Header sizes extend beyond boot image")
    cmdline = short_str(data[64:576]) + short_str(data[608:1632])
    report = {
        "path": str(path.resolve()),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "header_style": "Samsung/legacy Android header (interpreted as v0 with dt_size)",
        "page_size": page_size,
        "kernel_size": kernel_size,
        "kernel_offset": kernel_at,
        "ramdisk_size": ramdisk_size,
        "ramdisk_offset": ramdisk_at,
        "second_size": second_size,
        "dt_size": dt_size,
        "dt_offset": dt_at,
        "board_name": short_str(data[48:64]),
        "cmdline": cmdline,
        "detected_fdt": [],
        "ramdisk_files": [],
        "warnings": []
    }
    # Valid FDTs can appear in the explicit dt region or appended to the kernel.
    for idx in range(len(data) - 8):
        if data[idx:idx+4] != FDT_MAGIC:
            continue
        size = struct.unpack_from(">I", data, idx + 4)[0]
        if size < 40 or size > 2_000_000 or idx + size > len(data):
            continue
        if len(report["detected_fdt"]) >= 24:
            report["warnings"].append("Too many FDT candidates; stopped scanning")
            break
        name = f"fdt-{len(report['detected_fdt']):02d}-at-{idx}.dtb"
        dest = out / name
        dest.write_bytes(data[idx:idx+size])
        entry = {"offset": idx, "bytes": size, "file": name}
        if shutil.which("fdtget"):
            for prop in ("model", "compatible"):
                cp = subprocess.run(["fdtget", "-t", "s", str(dest), "/", prop], capture_output=True, text=True)
                if cp.returncode == 0:
                    entry[prop] = cp.stdout.strip()
        report["detected_fdt"].append(entry)
    ramdisk = data[ramdisk_at:ramdisk_at + ramdisk_size]
    try:
        if ramdisk.startswith(b"\x1f\x8b"):
            raw = gzip.decompress(ramdisk)
            report["ramdisk_compression"] = "gzip"
            report["ramdisk_decompressed_bytes"] = len(raw)
            report["ramdisk_files"], interesting = read_newc_entries(raw)
            for name, content in interesting.items():
                # Fixed output names: never use archive paths for filesystem writes.
                out_name = {"init": "INITRAMFS-init.txt", "bin/sh": "INITRAMFS-bin-sh-target.txt",
                            "etc/fstab": "INITRAMFS-fstab.txt", "etc/init": "INITRAMFS-etc-init.txt",
                            "etc/rc": "INITRAMFS-etc-rc.txt"}[name]
                (out / out_name).write_bytes(content)
            if "init" in interesting:
                report["init_first_line"] = interesting["init"].splitlines()[0].decode("utf-8", "replace") if interesting["init"] else ""
                text = interesting["init"].decode("utf-8", "replace")
                for needle in ("switch_root", "pivot_root", "sda31", "userdata", "PARTUUID", "/sbin/init", "root=", "devtmpfs"):
                    report.setdefault("init_references", {})[needle] = needle in text
        else:
            report["warnings"].append("Ramdisk is not gzip; listing unavailable")
    except Exception as exc:
        report["warnings"].append(f"Could not decompress initramfs: {exc}")
    names = {x["name"].lstrip("./") for x in report["ramdisk_files"]}
    for needed in ("init", "bin/sh", "bin/toybox"):
        if names and needed not in names:
            report["warnings"].append(f"initramfs does not list {needed} (symlinks may be different)")
    (out / "boot-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "ramdisk-file-list.txt").write_text("\n".join(e["name"] for e in report["ramdisk_files"]) + "\n")
    print(f"Android boot: {report['board_name']}; {report['bytes']} bytes; SHA256 {report['sha256']}")
    print(f"Kernel {kernel_size} bytes, ramdisk {ramdisk_size} bytes, page {page_size}; FDT candidates {len(report['detected_fdt'])}")
    print(f"Initramfs entries: {len(report['ramdisk_files'])}, warnings {len(report['warnings'])}")
    for issue in report["warnings"]: print("WARN:", issue)
    print("Report:", out / "boot-analysis.json")
    return report

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("boot-inspection"))
    args = ap.parse_args()
    try:
        inspect(args.image, args.out)
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
