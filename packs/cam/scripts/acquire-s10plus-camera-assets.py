#!/usr/bin/env python3
"""Read-only inventory/acquisition of camera vendor files from the owner's S10+.

This script runs on the development host and uses adb shell/find/stat/sha256sum
plus adb pull. It never mounts or writes phone partitions, never reboots, never
uses dd, and never reads /data, /efs, /persist, RPMB, raw EEPROM, TEE memory,
keystore material, or biometric/private user data.

Default mode is inventory-only. Pass --pull to copy matched ordinary files from
already-mounted vendor/system/odm filesystem directories to the host.
Device-specific dual-calibration blobs are excluded unless the operator passes
--include-vendor-calibration. Even then, only ordinary files in the allowlisted
vendor filesystem roots are considered; EEPROM and persist are never accessed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ALLOWED_ROOTS = (
    "/vendor/firmware", "/vendor/firmware_mnt", "/vendor/etc", "/vendor/bin/hw", "/vendor/lib", "/vendor/lib64",
    "/odm/firmware", "/odm/etc", "/odm/bin/hw", "/odm/lib", "/odm/lib64",
    "/system/vendor/firmware", "/system/vendor/firmware_mnt", "/system/vendor/etc", "/system/vendor/bin/hw",
    "/system/vendor/lib", "/system/vendor/lib64",
    "/system_root/vendor/firmware", "/system_root/vendor/firmware_mnt", "/system_root/vendor/etc", "/system_root/vendor/bin/hw",
    "/system_root/vendor/lib", "/system_root/vendor/lib64",
    "/system/etc", "/system/lib", "/system/lib64",
)

EXACT_NAMES = {
    "fimc_is_fw_mcu.bin", "fimc_is_lib.bin", "exynos9820_camera.bin",
    "is-camera.bin", "is-camera-3.bin", "camera_calibration.bin", "setfile.bin",
    "camera.exynos9820.so", "libexynoscamera3.so", "libacryl.so", "libcsc.so",
    "libhwjpeg.so", "libuniplugin.so", "libuniapi.so", "libhwjsqz.so",
    "libsensorlistener.so", "libsef.quram.so",
    "vendor.samsung.hardware.camera.provider@3.0-service",
    "vendor.samsung.hardware.camera.provider@3.0-service.rc",
}

PATTERNS = (
    re.compile(r"^s5k(2l4|3m3|3p9|3j1|4h7).*", re.I),
    re.compile(r"^fimc_is_(fw_mcu|lib|rta).*", re.I),
    re.compile(r"^is-camera(?:-.*)?\.bin$", re.I),
    re.compile(r"^setfile(?:[-_].*)?\.bin$", re.I),
    re.compile(r"^ois_fw.*\.bin$", re.I),
    re.compile(r"^camera.*\.(bin|xml|cfg|conf|json|ini)$", re.I),
    re.compile(r"^media_profiles.*\.xml$", re.I),
    re.compile(r"^camera\.device@.*\.so$", re.I),
    re.compile(r"^camera\.provider@.*\.so$", re.I),
    re.compile(r"^lib.*camera.*\.so$", re.I),
    re.compile(r"^vendor\.samsung\.hardware\.camera.*", re.I),
)
CAL_PATTERNS = (
    re.compile(r"^dual_cal.*", re.I),
    re.compile(r"^camera.*cal.*\.(bin|dat|img)$", re.I),
)

FORBIDDEN_PARTS = {
    "data", "efs", "persist", "metadata", "keymaster", "keystore", "rpmb",
    "qsee", "tee", "tzar", "trustlet", "secure", "biometric", "fingerprint",
}


def run(argv: list[str], *, check: bool = True, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout, check=check)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timed out: {argv[0]}") from exc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def adb_base(serial: str | None) -> list[str]:
    return ["adb"] + (["-s", serial] if serial else [])


def adb_shell(base: list[str], command: str, *, check: bool = True) -> str:
    cp = run(base + ["shell", command], check=check)
    return cp.stdout.replace("\r", "").strip()


def choose_device(serial_arg: str | None) -> tuple[str, list[str]]:
    if not shutil.which("adb"):
        raise RuntimeError("adb is not installed or not on PATH")
    cp = run(["adb", "devices", "-l"])
    devices = []
    for line in cp.stdout.splitlines()[1:]:
        cols = line.split()
        if len(cols) >= 2 and cols[1] == "device":
            devices.append(cols[0])
    if serial_arg:
        if serial_arg not in devices:
            raise RuntimeError(f"requested adb serial {serial_arg!r} is not in state 'device'")
        serial = serial_arg
    elif len(devices) == 1:
        serial = devices[0]
    elif not devices:
        raise RuntimeError("no adb device in state 'device'; connect the S10+ in TWRP and enable ADB")
    else:
        raise RuntimeError("multiple adb devices; specify --serial explicitly")
    return serial, adb_base(serial)


def get_identity(base: list[str]) -> dict[str, str]:
    raw = adb_shell(base, "getprop", check=False)
    props: dict[str, str] = {}
    for line in raw.splitlines():
        m = re.match(r"\[([^]]+)\]: \[(.*)\]$", line)
        if m:
            props[m.group(1)] = m.group(2)
    for key, path in (("device_tree_model", "/proc/device-tree/model"),
                      ("device_tree_compatible", "/proc/device-tree/compatible")):
        val = adb_shell(base, f"cat {path} 2>/dev/null | tr '\\000' ' '", check=False)
        if val:
            props[key] = val
    return props


def validate_identity(props: dict[str, str], confirm: bool) -> None:
    fields = " ".join(props.get(k, "") for k in (
        "ro.product.device", "ro.build.product", "ro.product.name",
        "ro.product.model", "ro.board.platform", "ro.hardware",
        "ro.boot.hardware", "device_tree_model", "device_tree_compatible")).lower()
    has_beyond = "beyond2lte" in fields or "beyond2ltexx" in fields
    has_exynos = "exynos9820" in fields or "universal9820" in fields
    has_model = "sm-g975f" in fields or "galaxy s10+" in fields or "galaxy s10 plus" in fields
    if has_beyond and (has_exynos or has_model):
        return
    if confirm:
        print("WARNING: properties did not conclusively identify beyond2lte/Exynos9820; proceeding only on explicit operator confirmation.", file=sys.stderr)
        return
    raise RuntimeError(
        "device identity is not conclusively SM-G975F/beyond2lte/Exynos9820. "
        "Check TWRP getprop/device-tree output; only after manually verifying the handset, rerun with --confirm-target."
    )


def list_remote_files(base: list[str], include_cal: bool) -> tuple[list[str], list[str]]:
    roots_present: list[str] = []
    all_candidates: set[str] = set()
    for root in ALLOWED_ROOTS:
        present = adb_shell(base, f"test -d '{root}' && echo yes || echo no", check=False)
        if present.strip() != "yes":
            continue
        roots_present.append(root)
        # Roots are hard-coded constants above, not user-controlled shell input.
        find_cmd = f"find '{root}' -maxdepth 5 -type f 2>/dev/null"
        result = adb_shell(base, find_cmd, check=False)
        for remote in result.splitlines():
            if not remote.startswith(root.rstrip("/") + "/"):
                continue
            name = Path(remote).name
            low = name.lower()
            if any(part in remote.lower().split("/") for part in FORBIDDEN_PARTS):
                continue
            if low in EXACT_NAMES or any(p.match(name) for p in PATTERNS):
                all_candidates.add(remote)
                continue
            if include_cal and any(p.match(name) for p in CAL_PATTERNS):
                all_candidates.add(remote)
    return sorted(roots_present), sorted(all_candidates)


def remote_metadata(base: list[str], remote: str) -> dict:
    quoted = shlex.quote(remote)
    size = adb_shell(base, f"stat -c %s {quoted} 2>/dev/null", check=False)
    digest = adb_shell(base, f"sha256sum {quoted} 2>/dev/null", check=False)
    sha = digest.split()[0] if digest and re.fullmatch(r"[0-9a-fA-F]{64}", digest.split()[0]) else None
    try:
        byte_size = int(size.split()[0])
    except (ValueError, IndexError):
        byte_size = None
    return {"remote_path": remote, "size_bytes": byte_size, "sha256_remote": sha}


def pull_file(base: list[str], remote: str, outdir: Path) -> dict:
    # Preserve the remote relative namespace below the first recognized root.
    root = next((r for r in ALLOWED_ROOTS if remote.startswith(r.rstrip("/") + "/")), None)
    if not root:
        raise RuntimeError(f"refusing path outside allowlist: {remote}")
    rel = Path(remote[len(root.rstrip("/")):].lstrip("/"))
    dest = outdir / "files" / root.strip("/") / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    cp = run(base + ["pull", remote, str(dest)], timeout=180)
    digest = sha256_file(dest)
    file_cmd = ["file", str(dest)] if shutil.which("file") else None
    file_desc = run(file_cmd, check=False).stdout.strip() if file_cmd else None
    elf_desc = None
    if file_desc and "ELF" in file_desc and shutil.which("readelf"):
        elf_desc = run(["readelf", "-h", "-l", "-d", str(dest)], check=False, timeout=30).stdout[:12000]
    return {
        "remote_path": remote, "local_path": str(dest),
        "size_bytes": dest.stat().st_size, "sha256_local": digest,
        "file": file_desc, "elf_readelf_excerpt": elf_desc,
        "adb_pull_stdout": cp.stdout.strip(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--serial", help="ADB serial (required if multiple devices are attached)")
    ap.add_argument("--output", default="./camera-acquisition", help="host output directory")
    ap.add_argument("--pull", action="store_true", help="copy matched ordinary vendor/system files to the host; default is inventory-only")
    ap.add_argument("--include-vendor-calibration", action="store_true",
                    help="also include camera calibration-named files found under allowlisted vendor/odm/system paths")
    ap.add_argument("--confirm-target", action="store_true",
                    help="manual confirmation after independently verifying the connected device is the SM-G975F Exynos beyond2lte")
    args = ap.parse_args()

    try:
        serial, base = choose_device(args.serial)
        identity = get_identity(base)
        validate_identity(identity, args.confirm_target)
        roots, candidates = list_remote_files(base, args.include_vendor_calibration)
        outdir = Path(args.output).expanduser().resolve()
        outdir.mkdir(parents=True, exist_ok=True)
        entries = []
        for remote in candidates:
            meta = remote_metadata(base, remote)
            if args.pull:
                pulled = pull_file(base, remote, outdir)
                if meta.get("sha256_remote") and pulled["sha256_local"] != meta["sha256_remote"]:
                    raise RuntimeError(f"hash mismatch after adb pull: {remote}")
                meta.update(pulled)
            entries.append(meta)

        doc = {
            "schema_version": 1,
            "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "device_serial_redacted": True,
            "adb_serial": "REDACTED",
            "identity_properties": identity,
            "allowed_roots_present": roots,
            "allowed_roots_not_mounted_or_missing": [r for r in ALLOWED_ROOTS if r not in roots],
            "mode": "pull" if args.pull else "inventory_only",
            "include_vendor_calibration": bool(args.include_vendor_calibration),
            "candidate_count": len(entries),
            "files": entries,
            "safety": {
                "phone_partition_writes": False,
                "mount_operations": False,
                "reboot": False,
                "dd_or_raw_block_access": False,
                "accessed_paths": "Only regular files found below the hard-coded vendor/system/odm roots in this script.",
                "excluded": ["/data", "/efs", "/persist", "RPMB", "raw EEPROM", "TEE memory", "keystore", "user biometric/media data"],
            },
        }
        (outdir / "manifest.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(f"device: verified target family; ADB serial redacted")
        print(f"vendor/system roots present: {len(roots)}")
        print(f"camera candidates: {len(entries)}")
        print(f"mode: {'PULLED TO HOST' if args.pull else 'INVENTORY ONLY'}")
        print(f"manifest: {outdir / 'manifest.json'}")
        for item in entries:
            print(f"{item['remote_path']}  size={item.get('size_bytes')} sha256={item.get('sha256_local') or item.get('sha256_remote') or 'unavailable'}")
        if not roots:
            print("No allowlisted vendor/system roots are mounted. This script did not mount anything. Use TWRP's verified read-only mount UI/flow, then rerun.", file=sys.stderr)
        if not candidates:
            print("No matching camera files were found in the already-mounted allowlisted roots. This is not proof that the stock firmware lacks them.", file=sys.stderr)
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"acquisition failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
