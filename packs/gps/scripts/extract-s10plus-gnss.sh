#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: extract-s10plus-gnss.sh STOCK_ROOTFS [OUTPUT_DIR]

STOCK_ROOTFS is a read-only extracted/mounted Android filesystem for SM-G975F.
It may contain vendor/ and system/vendor/, or it may itself be the vendor
partition root (bin/, etc/, lib/, lib64/). This script does not unpack Samsung
firmware archives, sparse images, LZ4 images, or super.img.

Writes only under OUTPUT_DIR (default ./s10plus-gnss-extracted).
USAGE
}

[[ $# -ge 1 && $# -le 2 ]] || { usage >&2; exit 64; }
ROOT=$(cd "$1" && pwd -P)
OUT=${2:-./s10plus-gnss-extracted}
mkdir -p "$OUT/payload/vendor" "$OUT/payload/system" "$OUT/payload/unverified-firmware-candidates"
OUT=$(cd "$OUT" && pwd -P)
REPORT="$OUT/extraction-report.txt"
: > "$REPORT"

log() { printf '%s\n' "$*" | tee -a "$REPORT"; }

# Reject an accidentally supplied Nuxel rootfs or a different Samsung model.
identity_files=(
  "$ROOT/build.prop" "$ROOT/default.prop"
  "$ROOT/system/build.prop" "$ROOT/vendor/build.prop"
  "$ROOT/product/build.prop" "$ROOT/system/vendor/build.prop"
)
identity_text=""
for f in "${identity_files[@]}"; do
  if [[ -f "$f" ]]; then identity_text+=$(grep -E 'ro\.(product\.(model|device|name)|vendor\.build\.fingerprint|build\.fingerprint)' "$f" 2>/dev/null || true); identity_text+=$'\n'; fi
done
if grep -Eqi 'SM-G975N|beyond2ltexx' <<<"$identity_text"; then
  echo "ERROR: source identifies as SM-G975N/beyond2ltexx, not target SM-G975F/beyond2lte." >&2
  exit 65
fi
if ! grep -Eqi 'SM-G975F|beyond2lte' <<<"$identity_text"; then
  if [[ "${ALLOW_UNVERIFIED_SOURCE:-0}" != "1" ]]; then
    echo "ERROR: cannot verify source is SM-G975F/beyond2lte from build.prop." >&2
    echo "Use an exact G975F stock filesystem, or set ALLOW_UNVERIFIED_SOURCE=1 only after independently checking its model/build." >&2
    exit 65
  fi
fi

# Find a target path across common Android image layouts. Output is the real file path.
find_target() {
  local rel="$1" p
  local candidates=(
    "$ROOT/$rel"
    "$ROOT/system/$rel"
    "$ROOT/root/$rel"
  )
  # If ROOT itself is a mounted vendor partition, strip the leading vendor/.
  if [[ "$rel" == vendor/* ]]; then
    candidates+=("$ROOT/${rel#vendor/}")
  fi
  # Some unpackers put the vendor partition below vendor.img/ or vendor_root/.
  candidates+=("$ROOT/vendor_root/${rel#vendor/}" "$ROOT/vendor.img/${rel#vendor/}")
  for p in "${candidates[@]}"; do
    if [[ -f "$p" ]]; then printf '%s\n' "$p"; return 0; fi
  done
  return 1
}

copy_target() {
  local rel="$1" src dest
  if src=$(find_target "$rel"); then
    dest="$OUT/payload/$rel"
    mkdir -p "$(dirname "$dest")"
    cp -L -- "$src" "$dest"
    log "FOUND  $rel  <-  ${src#"$ROOT"/}"
    return 0
  else
    log "MISSING $rel"
    return 1
  fi
}

log "Nuxel S10+ GNSS extraction"
log "source_root=$ROOT"
log "target=SM-G975F/beyond2lte"
if grep -Eqi 'SM-G975F|beyond2lte' <<<"$identity_text"; then
  log "source_identity=matched_build_prop"
else
  log "source_identity=operator_override_UNVERIFIED"
fi
log "mode=read-only source; output=$OUT"
log ""

# Known vendor files from the beyond2lte build recipe / S10-family manifests.
paths=(
  vendor/bin/hw/lhd
  vendor/bin/hw/gpsd
  vendor/bin/hw/vendor.samsung.hardware.gnss@2.0-service
  vendor/etc/gnss/gps.xml
  vendor/etc/gnss/gps.cer
  vendor/etc/init/init.gps.rc
  vendor/etc/init/vendor.samsung.hardware.gnss@2.0-service.rc
  vendor/etc/sensor/lhd.conf
  vendor/lib64/hw/gps.default.so
  vendor/lib64/hw/android.hardware.gnss@2.0-impl.so
  vendor/lib64/hw/vendor.samsung.hardware.gnss@2.0-impl.so
  vendor/lib64/vendor.samsung.hardware.gnss@2.0.so
  vendor/lib64/libwrappergps.so
  vendor/lib64/sensors.sensorhub.so
  vendor/lib/hw/gps.default.so
  vendor/lib/hw/android.hardware.gnss@2.0-impl.so
  vendor/lib/hw/vendor.samsung.hardware.gnss@2.0-impl.so
  vendor/lib/vendor.samsung.hardware.gnss@2.0.so
  vendor/lib/libwrappergps.so
  vendor/lib/sensors.sensorhub.so
  system/bin/linker64
  system/bin/linker
)
found=0
for rel in "${paths[@]}"; do
  if copy_target "$rel"; then found=$((found+1)); fi
done

# Capture GNSS-related VINTF/permission metadata, when present. These XML files
# help identify declared HAL instances and service versioning; they are not proof
# that a vendor service can run outside Android.
log ""
log "GNSS VINTF / permission metadata"
while IFS= read -r -d '' f; do
  rel=${f#"$ROOT"/}
  dest="$OUT/payload/$rel"
  mkdir -p "$(dirname "$dest")"
  cp -L -- "$f" "$dest"
  log "FOUND-METADATA $rel"
  found=$((found+1))
done < <(find "$ROOT/vendor/etc/vintf" "$ROOT/vendor/etc/permissions" "$ROOT/system/vendor/etc/vintf" \
  -type f \( -iname '*gnss*.xml' -o -iname '*gps*.xml' -o -name 'manifest.xml' \) -print0 2>/dev/null || true)

# Find firmware names only as unverified candidates. Preserve source-relative path
# in destination to make provenance review possible. Never call these validated.
log ""
log "UNVERIFIED SENSOR-HUB FIRMWARE CANDIDATES (not safe to load until matched)"
fw_found=0
while IFS= read -r -d '' f; do
  base=$(basename "$f")
  rel=${f#"$ROOT"/}
  # Guard against duplicate basenames by placing a sanitized source path below dest.
  safe_rel=${rel//\//__}
  cp -L -- "$f" "$OUT/payload/unverified-firmware-candidates/$safe_rel"
  log "CANDIDATE $rel -> payload/unverified-firmware-candidates/$safe_rel"
  fw_found=$((fw_found+1))
done < <(find "$ROOT" -type f \( \
  -iname 'SensorHub*.patch' -o -iname '*sensorhub*.patch' -o \
  -iname 'bcm4773*.patch' -o -iname 'bcm47752*.patch' -o \
  -iname '*sensorhub*.bin' -o -iname 'bcm_sensorhub_a1.patch' \
  \) -print0 2>/dev/null)
if [[ $fw_found -eq 0 ]]; then log "NONE FOUND"; fi

log ""
log "summary_vendor_files_found=$found"
log "summary_unverified_firmware_candidates=$fw_found"
log "IMPORTANT: file presence/name does not verify model, chip, build, revision, or loader compatibility."

# Create an extraction marker; it signals only that the script completed.
printf 'files_found=%s\nfirmware_candidates=%s\nsource_root=%s\n' "$found" "$fw_found" "$ROOT" > "$OUT/EXTRACTION_COMPLETED_NOT_VERIFIED.txt"

# Hash all extracted files for follow-up comparison/provenance.
if command -v sha256sum >/dev/null 2>&1; then
  (cd "$OUT" && find payload -type f -print0 | sort -z | xargs -0 -r sha256sum > SHA256SUMS)
fi

log ""
log "output=$OUT"
log "No device was accessed; no firmware was loaded; no flash operation was run."
