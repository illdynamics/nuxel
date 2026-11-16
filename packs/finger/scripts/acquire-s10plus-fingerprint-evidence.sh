#!/usr/bin/env bash
# Read-only evidence/acquisition helper for the Samsung Galaxy S10+ Exynos QBT2000 stack.
# The phone is never modified. The script writes only to the host workstation.
set -Eeuo pipefail

ADB_BIN="${ADB:-adb}"
OUT_DIR="${1:-./fingerprint-acquisition}"
if [[ -e "$OUT_DIR" ]]; then OUT_DIR="${OUT_DIR}-$(date -u +%Y%m%dT%H%M%SZ)"; fi
mkdir -p "$OUT_DIR/files"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

command -v "$ADB_BIN" >/dev/null 2>&1 || { echo "ERROR: adb not found" >&2; exit 2; }

mapfile -t SERIALS < <("$ADB_BIN" devices | awk 'NR>1 && $2=="device" {print $1}')
if [[ -n "${ADB_SERIAL:-}" ]]; then
  SERIAL="$ADB_SERIAL"
  printf '%s\n' "${SERIALS[@]}" | grep -Fxq "$SERIAL" || { echo "ERROR: ADB_SERIAL is not an authorized connected 'device' transport" >&2; exit 2; }
else
  [[ ${#SERIALS[@]} -eq 1 ]] || {
    echo "ERROR: expected exactly one authorized adb device; found ${#SERIALS[@]}" >&2
    echo "Set ADB_SERIAL only after verifying the S10+ identity. TWRP may require adb authorization/root." >&2
    exit 2
  }
  SERIAL="${SERIALS[0]}"
fi
adb_cmd() { "$ADB_BIN" -s "$SERIAL" "$@"; }

cat > "$OUT_DIR/README.txt" <<README
Nuxel S10+ fingerprint / TEE evidence acquisition

This script queried a single connected ADB device and copied only whitelisted
ordinary files found under /vendor, /system/vendor, /odm, /system/lib*, and
system/vendor executable directories whose names match fingerprint/QBT/TEE
client/TA terms. The script never writes to the phone.

It does NOT access or copy /data, /efs, /persist, RPMB, keystore/biometric
user storage, raw TEE memory, signing keys, or raw QBT device-node contents.
It does not mount partitions, alter permissions, load a TA, write firmware,
flash a partition, reboot, or touch the bootloader.

ADB serial: $SERIAL
Captured UTC: $(date -u +%FT%TZ)

Review device identity. In TWRP, properties may be incomplete; do not treat a
blank ro.product.device as proof of a different device. Verify the actual
handset/model before using any acquired payload.
README

{
  echo "# ADB devices"
  adb_cmd devices -l || true
  echo
  echo "# Identity/build properties (serial/IMEI properties intentionally excluded)"
  adb_cmd shell getprop 2>/dev/null | tr -d '\r' | grep -Ei '^\[(ro\.product\.(device|model|manufacturer|name)|ro\.build\.(fingerprint|id|display\.id|version\.release|version\.sdk|version\.security_patch)|ro\.vendor\.build\.(fingerprint|id)|ro\.boot\.(hardware|verifiedbootstate|vbmeta\.device_state)|ro\.hardware|ro\.soc\.model)\]:' || true
  echo
  echo "# Kernel identity"
  adb_cmd shell 'uname -a; cat /proc/version 2>/dev/null' 2>/dev/null | tr -d '\r' || true
  echo
  echo "# Relevant mounts (read-only observation only)"
  adb_cmd shell 'mount 2>/dev/null | grep -E " on /(vendor|system|odm)(/| )| on /system/vendor"' 2>/dev/null | tr -d '\r' || true
  echo
  echo "# Fingerprint device nodes (names/permissions only; no device data read)"
  adb_cmd shell 'ls -l /dev/qbt2000_fd /dev/qbt2000_ipc /dev/tzdev /dev/tziwsock /dev/tee* /dev/tz* 2>/dev/null' 2>/dev/null | tr -d '\r' || true
  echo
  echo "# Fingerprint sysfs diagnostics (no scan data)"
  adb_cmd shell 'for f in /sys/class/fingerprint/fingerprint/name /sys/class/fingerprint/fingerprint/vendor /sys/class/fingerprint/fingerprint/type_check /sys/class/fingerprint/fingerprint/position /sys/class/fingerprint/fingerprint/adm /sys/class/fingerprint/fingerprint/bfs_values; do if [ -r "$f" ]; then printf "%s=" "$f"; cat "$f"; fi; done' 2>/dev/null | tr -d '\r' || true
  echo
  echo "# Kernel log lines mentioning the fingerprint driver or TEE startup"
  adb_cmd shell 'dmesg 2>/dev/null | grep -Ei "qbt2000|fingerprint|fps_|TEEGRIS|TZDEV|tzdev|tziwsock|startup_loader|startup\.tzar|libtzld|trustlet" | tail -n 500' 2>/dev/null | tr -d '\r' || true
} > "$OUT_DIR/device-diagnostics.txt"

# Inventory only ordinary, readable vendor/system file paths. No /data, /efs,
# /persist, RPMB, key stores, secure RAM, raw partitions or /dev contents.
ROOTS=(/vendor /system/vendor /odm /system/lib /system/lib64 /system/bin /system/bin/hw)
REMOTE_LIST="$OUT_DIR/candidate-files-remote.txt"
: > "$REMOTE_LIST"
for root in "${ROOTS[@]}"; do
  adb_cmd shell "if [ -d '$root' ]; then find '$root' -type f 2>/dev/null; fi" 2>/dev/null \
    | tr -d '\r' \
    | grep -Ei '/[^/]*(finger(print)?|qbt[0-9]*|biometric|teegris|teecl|tzdev|tziwsock|tzar|trust(let|zone)?|keymaster|gatekeeper|fps)[^/]*$' \
    >> "$REMOTE_LIST" || true
done
sort -u "$REMOTE_LIST" -o "$REMOTE_LIST"

# Cap number of artifacts to avoid accidentally creating a broad vendor dump.
mapfile -t CANDIDATES < <(head -n 500 "$REMOTE_LIST")
printf 'Candidate count (capped at 500): %s\n' "${#CANDIDATES[@]}" > "$OUT_DIR/acquisition-summary.txt"
: > "$OUT_DIR/file-manifest.tsv"
for remote in "${CANDIDATES[@]}"; do
  # Strict allowlist: only regular files under the normal read-only vendor/system trees.
  case "$remote" in
    /vendor/*|/system/vendor/*|/odm/*|/system/lib/*|/system/lib64/*|/system/bin/*) ;;
    *) continue ;;
  esac
  [[ "$remote" != *"/../"* && "$remote" != *"/./"* ]] || continue
  dest="$OUT_DIR/files$remote"
  mkdir -p "$(dirname "$dest")"
  if adb_cmd pull "$remote" "$dest" >/dev/null 2>&1; then
    if command -v sha256sum >/dev/null 2>&1; then hash="$(sha256sum "$dest" | awk '{print $1}')"; else hash="unavailable"; fi
    size="$(wc -c < "$dest" | tr -d ' ')"
    printf '%s\t%s\t%s\n' "$remote" "$size" "$hash" >> "$OUT_DIR/file-manifest.tsv"
    if command -v file >/dev/null 2>&1; then file -b "$dest" 2>/dev/null | sed "s|^|$remote\t|" >> "$OUT_DIR/file-types.txt"; fi
    if command -v readelf >/dev/null 2>&1 && readelf -h "$dest" >/dev/null 2>&1; then
      { echo "### $remote"; readelf -h "$dest" 2>/dev/null | grep -E 'Class:|Data:|Machine:|OS/ABI:' || true; readelf -l "$dest" 2>/dev/null | grep -E 'INTERP|Requesting program interpreter' || true; readelf -d "$dest" 2>/dev/null | grep NEEDED || true; } >> "$OUT_DIR/elf-details.txt"
    fi
  else
    printf '%s\tPULL_FAILED\t-\n' "$remote" >> "$OUT_DIR/file-manifest.tsv"
  fi
done

{
  echo "Acquired files: $(grep -c $'\t[0-9]' "$OUT_DIR/file-manifest.tsv" 2>/dev/null || true)"
  echo "Pull failures: $(grep -c 'PULL_FAILED' "$OUT_DIR/file-manifest.tsv" 2>/dev/null || true)"
  echo "No firmware/TA has been created by this tool."
  echo "Files under normal vendor/system paths are evidence only; verify signature, source, ABI, build and device compatibility before use."
} >> "$OUT_DIR/acquisition-summary.txt"

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUT_DIR" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 -r sha256sum) > "$OUT_DIR/SHA256SUMS"
fi

echo "Read-only acquisition complete: $OUT_DIR"
echo "Review device-diagnostics.txt, file-manifest.tsv and SHA256SUMS. No phone partitions or device nodes were modified/read as biometric data."
