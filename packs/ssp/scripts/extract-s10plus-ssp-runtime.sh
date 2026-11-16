#!/usr/bin/env bash
set -euo pipefail

ADB_BIN="${ADB:-adb}"
OUT="./S10Plus-SSP-Runtime"
SERIAL=""

usage() {
  cat <<'USAGE'
Usage: extract-s10plus-ssp-runtime.sh [--out DIR] [--serial SERIAL]

Read-only extraction from a connected SM-G975F / beyond2lte over ADB.
Ensure /vendor is mounted read-only in TWRP (and /system if available).
This script never mounts, writes, executes vendor code, flashes or reboots.
USAGE
}
while (($#)); do
  case "$1" in
    --out) OUT="${2:?missing directory after --out}"; shift 2 ;;
    --serial) SERIAL="${2:?missing serial after --serial}"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
command -v "$ADB_BIN" >/dev/null 2>&1 || { echo "adb not found. Install Android platform-tools." >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required." >&2; exit 2; }

adb_cmd() {
  if [[ -n "$SERIAL" ]]; then "$ADB_BIN" -s "$SERIAL" "$@"; else "$ADB_BIN" "$@"; fi
}

DEVICES=()
while IFS= read -r dev; do
  [[ -n "$dev" ]] && DEVICES+=("$dev")
done < <("$ADB_BIN" devices | awk 'NR>1 && $2=="device" {print $1}')
if [[ -z "$SERIAL" ]]; then
  if ((${#DEVICES[@]} != 1)); then
    echo "Expected exactly one online ADB device; found ${#DEVICES[@]}. Use --serial SERIAL." >&2
    "$ADB_BIN" devices >&2
    exit 3
  fi
  SERIAL="${DEVICES[0]}"
else
  printf '%s\n' "${DEVICES[@]}" | grep -Fxq "$SERIAL" || {
    echo "Requested serial '$SERIAL' is not an online ADB device." >&2
    "$ADB_BIN" devices >&2
    exit 3
  }
fi

remote_prop() { adb_cmd shell getprop "$1" 2>/dev/null | tr -d '\r'; }
DEVICE="$(remote_prop ro.product.device)"
PRODUCT="$(remote_prop ro.product.name)"
MODEL="$(remote_prop ro.product.model)"
if [[ "$DEVICE" != "beyond2lte" && ! "$PRODUCT" =~ ^beyond2lte ]]; then
  echo "Identity check failed: ro.product.device='$DEVICE', ro.product.name='$PRODUCT'." >&2
  echo "Expected Samsung beyond2lte / SM-G975F. No files were pulled." >&2
  exit 4
fi

mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
mkdir -p "$OUT/vendor" "$OUT/system" "$OUT/reports"

{
  echo "serial=$SERIAL"
  echo "ro.product.device=$DEVICE"
  echo "ro.product.name=$PRODUCT"
  echo "ro.product.model=$MODEL"
  for p in ro.board.platform ro.hardware ro.bootloader ro.build.version.release ro.build.version.sdk ro.build.fingerprint ro.vendor.build.fingerprint; do
    echo "$p=$(remote_prop "$p")"
  done
  echo "capture_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host=$(uname -srm)"
} > "$OUT/reports/device-info.txt"

pull_one() {
  local remote="$1" rel="${1#/}" localpath="$OUT/${1#/}"
  if adb_cmd shell test -r "$remote" >/dev/null 2>&1; then
    mkdir -p "$(dirname "$localpath")"
    if adb_cmd pull "$remote" "$localpath" >/dev/null; then
      echo "PULLED $remote"
      return 0
    fi
    echo "PULL_FAILED $remote" | tee -a "$OUT/reports/collection-status.txt"
  else
    echo "MISSING $remote" | tee -a "$OUT/reports/collection-status.txt"
  fi
  return 1
}

: > "$OUT/reports/collection-status.txt"
# Primary target-specific runtime and configuration.
CORE_FILES=(
  /vendor/bin/hw/lhd
  /vendor/bin/lhd
  /vendor/etc/sensor/lhd.conf
  /vendor/etc/sensors/hals.conf
  /vendor/lib64/sensors.sensorhub.so
  /vendor/lib/sensors.sensorhub.so
  /vendor/lib64/hw/sensors.exynos9820.so
  /vendor/lib/hw/sensors.exynos9820.so
  /vendor/etc/init/init.gps.rc
  /vendor/etc/init/init.sensor.rc
  /vendor/etc/init/init.sensors.rc
  /vendor/etc/init/init.sensorhub.rc
  /vendor/etc/vintf/manifest.xml
  /vendor/firmware/SensorHub.patch
  /vendor/firmware/gnss/SensorHub.patch
  /vendor/firmware/gnss/bcm4773_sensorhub.patch
  /system/bin/linker64
  /system/bin/linker
)
for f in "${CORE_FILES[@]}"; do pull_one "$f" || true; done

# Find other init/VINTF files that explicitly mention lhd or sensor hub.
for base in /vendor/etc/init /vendor/etc/vintf; do
  if adb_cmd shell test -d "$base" >/dev/null 2>&1; then
    remote_list="$(adb_cmd shell "grep -RIlE 'lhd|sensorhub|bbd_control|bbd_patch' '$base' 2>/dev/null | head -80" | tr -d '\r' || true)"
    while IFS= read -r f; do
      [[ "$f" == /* ]] || continue
      pull_one "$f" || true
    done <<< "$remote_list"
  fi
done

# Resolve DT_NEEDED recursively against the matching device's own Android
# system/vendor library directories. This copies only libraries named by the
# collected ELF files; it does not copy entire /system or /vendor partitions.
python3 "$(dirname "$0")/collect-elf-deps.py" \
  --adb "$ADB_BIN" --serial "$SERIAL" --root "$OUT" \
  2>&1 | tee "$OUT/reports/elf-dependency-collection.txt" || true

python3 "$(dirname "$0")/verify-s10plus-ssp-runtime.py" --root "$OUT" \
  2>&1 | tee "$OUT/reports/verification.txt" || true

# Hash every collected file and package the evidence. SHA256SUMS is generated
# for the recipient; no device writes were performed.
python3 - "$OUT" <<'PYHASH' > "$OUT/SHA256SUMS.txt"
import hashlib, os, sys
root = os.path.abspath(sys.argv[1])
paths = []
for base, dirs, files in os.walk(root):
    dirs.sort()
    for name in files:
        if name == "SHA256SUMS.txt":
            continue
        path = os.path.join(base, name)
        if os.path.commonpath([root, path]) == root:
            paths.append(path)
for path in sorted(paths):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    print(f"{h.hexdigest()}  {os.path.relpath(path, root)}")
PYHASH

ZIP_OUT="${OUT%/*}/$(basename "$OUT")-extracted.zip"
python3 - "$OUT" "$ZIP_OUT" <<'PY'
import os, sys, zipfile
root, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for base, dirs, files in os.walk(root):
        dirs.sort(); files.sort()
        for name in files:
            path = os.path.join(base, name)
            z.write(path, os.path.relpath(path, os.path.dirname(root)))
print(out)
PY

echo
echo "Extraction complete: $OUT"
echo "Evidence ZIP:       $ZIP_OUT"
echo "Review reports/verification.txt before giving the archive to the agent."
echo "No device partitions or files were modified."
