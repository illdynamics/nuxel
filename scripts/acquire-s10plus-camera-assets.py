
#!/usr/bin/env python3
"""
acquire-s10plus-camera-assets.py

Conservative Samsung Galaxy S10+ (SM-G975F / beyond2lte / Exynos 9820)
camera firmware inventory and acquisition helper.

Default: inventory only.
--pull: copy matching ordinary files from already-mounted stock partitions.
--include-vendor-calibration: additionally include matching vendor calibration
                              files (requires --pull).

This script NEVER mounts partitions, writes to the phone, flashes, reboots,
uses dd, or accesses EFS, persist, RPMB, TEE memory, raw EEPROM or user media.

The candidate patterns are discovery hints, not proof of compatibility.
Every acquired file must be verified against the exact kernel driver request
and matching stock firmware build before it is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


DEVICE_EXPECTATIONS = {
    "model": "SM-G975F",
    "device": "beyond2lte",
}

SEARCH_ROOTS = (
    "/vendor",
    "/odm",
    "/system/vendor",
    "/system/odm",
)

# Candidate names based on the S10+ Exynos FIMC-IS investigation.
# Verify the exact requested names in the pinned kernel source.
CAMERA_PATTERNS = (
    "*s5k2l4*",
    "*s5k3m3*",
    "*s5k3p9*",
    "*s5k3j1*",
    "*s5k4h7*",
    "*fimc*is*",
    "*exynos9820*camera*",
    "*is-camera*",
    "*setfile*",
    "*ois*",
    "*camera*firmware*",
    "*camera*fw*",
    "*camera*tuning*",
)

CALIBRATION_PATTERNS = (
    "*camera*calib*",
    "*cam*calib*",
    "*ois*calib*",
    "*sensor*calib*",
    "*eeprom*calib*",
)

EXCLUDED_PATH_PARTS = {
    "dcim",
    "pictures",
    "movies",
    "camera",
    "screenshots",
    "thumbnails",
    "cache",
    "data",
    "media",
    "efs",
    "persist",
    "metadata",
}

MAX_FILE_SIZE = 128 * 1024 * 1024  # 128 MiB safety limit


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def adb_shell(command: str, *, check: bool = True) -> str:
    result = run(["adb", "shell", command], check=check)
    return result.stdout.replace("\r", "").strip()


def check_adb() -> None:
    if shutil.which("adb") is None:
        raise RuntimeError("adb was not found. Install Android platform-tools.")

    result = run(["adb", "devices", "-l"])
    devices = []

    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "device":
            devices.append(fields[0])
        elif len(fields) >= 2 and fields[1] == "recovery":
            devices.append(fields[0])

    if len(devices) != 1:
        raise RuntimeError(
            "Expected exactly one connected ADB device in TWRP/recovery mode. "
            f"Found: {devices or 'none'}. Disconnect other devices."
        )


def get_property(name: str) -> str:
    return adb_shell(f"getprop {name}", check=False)


def verify_device_identity() -> dict:
    props = {
        "model": get_property("ro.product.model"),
        "device": get_property("ro.product.device"),
        "product": get_property("ro.build.product"),
        "hardware": get_property("ro.hardware"),
        "soc": get_property("ro.board.platform"),
    }

    print("\nDevice properties:")
    for key, value in props.items():
        print(f"  {key}: {value or '(not exposed by recovery)'}")

    model_values = {
        props["model"].upper(),
        props["device"].lower(),
        props["product"].lower(),
    }

    identity_evidence = any(
        value in {"SM-G975F", "beyond2lte"}
        for value in model_values
    )

    if not identity_evidence:
        print(
            "\nWARNING: TWRP properties did not positively identify "
            "SM-G975F/beyond2lte."
        )
        print(
            "Confirm the physical handset and recovery identity before "
            "using --pull."
        )

    return {
        "properties": props,
        "identity_confirmed_by_properties": identity_evidence,
    }


def remote_roots() -> list[str]:
    found = []

    for root in SEARCH_ROOTS:
        exists = adb_shell(
            f"test -d '{root}' && echo yes || echo no",
            check=False,
        )
        if exists == "yes":
            found.append(root)

    return found


def make_find_command(roots: list[str], patterns: tuple[str, ...]) -> str:
    root_args = " ".join(f"'{root}'" for root in roots)

    pattern_args = " -o ".join(
        f"-iname '{pattern}'" for pattern in patterns
    )

    return (
        f"find {root_args} -type f "
        f"\\( {pattern_args} \\) -print 2>/dev/null"
    )


def is_calibration_path(path: str) -> bool:
    lower = path.lower()
    return any(
        re.search(pattern.replace("*", ".*"), lower)
        for pattern in CALIBRATION_PATTERNS
    )


def excluded_path(path: str) -> bool:
    parts = {part.lower() for part in PurePosixPath(path).parts}
    return bool(parts & EXCLUDED_PATH_PARTS)


def inventory_files(
    roots: list[str],
    include_calibration: bool,
) -> list[str]:
    patterns = CAMERA_PATTERNS
    if include_calibration:
        patterns += CALIBRATION_PATTERNS

    command = make_find_command(roots, patterns)
    output = adb_shell(command, check=False)

    results = []

    for line in output.splitlines():
        path = line.strip()

        if not path.startswith("/"):
            continue

        if excluded_path(path):
            continue

        if not include_calibration and is_calibration_path(path):
            continue

        if path not in results:
            results.append(path)

    return sorted(results)


def remote_file_size(path: str) -> int | None:
    # TWRP's toolbox/toybox usually supports stat -c.
    result = adb_shell(
        f"stat -c '%s' '{path}' 2>/dev/null",
        check=False,
    )

    try:
        return int(result.splitlines()[-1])
    except (ValueError, IndexError):
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def pull_file(remote_path: str, output_root: Path) -> dict:
    relative = PurePosixPath(remote_path).relative_to("/")
    destination = output_root / "files" / Path(*relative.parts)

    destination.parent.mkdir(parents=True, exist_ok=True)

    size = remote_file_size(remote_path)

    if size is None:
        return {
            "source": remote_path,
            "status": "SKIPPED_SIZE_UNKNOWN",
        }

    if size <= 0:
        return {
            "source": remote_path,
            "status": "SKIPPED_EMPTY",
            "size": size,
        }

    if size > MAX_FILE_SIZE:
        return {
            "source": remote_path,
            "status": "SKIPPED_TOO_LARGE",
            "size": size,
            "limit": MAX_FILE_SIZE,
        }

    print(f"Pulling {remote_path} ({size:,} bytes)")

    result = run(
        ["adb", "pull", remote_path, str(destination)],
        check=False,
    )

    if result.returncode != 0 or not destination.is_file():
        return {
            "source": remote_path,
            "status": "PULL_FAILED",
            "stderr": result.stderr.strip(),
        }

    actual_size = destination.stat().st_size

    if actual_size != size:
        destination.unlink(missing_ok=True)
        return {
            "source": remote_path,
            "status": "SIZE_MISMATCH",
            "expected_size": size,
            "actual_size": actual_size,
        }

    return {
        "source": remote_path,
        "local_path": str(destination),
        "status": "PULLED",
        "size": actual_size,
        "sha256": sha256_file(destination),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory/acquire S10+ camera firmware candidates."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./camera-acquisition"),
        help="Output directory (default: ./camera-acquisition)",
    )

    parser.add_argument(
        "--pull",
        action="store_true",
        help="Actually copy discovered files from the connected phone.",
    )

    parser.add_argument(
        "--include-vendor-calibration",
        action="store_true",
        help="Include matching ordinary vendor calibration files.",
    )

    args = parser.parse_args()

    if args.include_vendor_calibration and not args.pull:
        parser.error(
            "--include-vendor-calibration requires --pull"
        )

    try:
        check_adb()

        identity = verify_device_identity()

        roots = remote_roots()

        if not roots:
            raise RuntimeError(
                "No supported vendor/system/odm roots are mounted. "
                "This script will not mount partitions. "
                "Use a verified read-only TWRP mount procedure, then retry."
            )

        print("\nMounted search roots:")
        for root in roots:
            print(f"  {root}")

        files = inventory_files(
            roots,
            include_calibration=args.include_vendor_calibration,
        )

        print(f"\nFound {len(files)} candidate files:\n")

        for path in files:
            size = remote_file_size(path)
            size_text = f"{size:,} bytes" if size is not None else "size unknown"
            print(f"  {path}  [{size_text}]")

        if not files:
            print(
                "\nNo candidate files found. This does not prove the "
                "firmware is absent: exact names may differ. Compare "
                "the kernel firmware requests and stock vendor image."
            )

        manifest = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "device_expectations": DEVICE_EXPECTATIONS,
            "device": identity,
            "search_roots": roots,
            "mode": "pull" if args.pull else "inventory_only",
            "calibration_included": args.include_vendor_calibration,
            "warning": (
                "Candidate discovery is not compatibility proof. "
                "Verify every file against the exact SM-G975F kernel "
                "loader, stock firmware build and ABI."
            ),
            "files": [],
        }

        args.output.mkdir(parents=True, exist_ok=True)

        if args.pull:
            print("\nStarting file acquisition...\n")

            for index, remote_path in enumerate(files, start=1):
                print(f"[{index}/{len(files)}]")
                manifest["files"].append(
                    pull_file(remote_path, args.output)
                )
        else:
            for remote_path in files:
                manifest["files"].append({
                    "source": remote_path,
                    "size": remote_file_size(remote_path),
                    "status": "INVENTORIED_NOT_COPIED",
                })

        manifest_path = args.output / "camera-acquisition-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"\nManifest: {manifest_path}")

        if args.pull:
            pulled = sum(
                item["status"] == "PULLED"
                for item in manifest["files"]
            )
            print(f"Successfully acquired: {pulled}/{len(files)} files")

        print(
            "\nIMPORTANT: Do not install these files yet. Verify exact "
            "firmware names, hashes, format, provenance and driver "
            "compatibility first."
        )

        return 0

    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

