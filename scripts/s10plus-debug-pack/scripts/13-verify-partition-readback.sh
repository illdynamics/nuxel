#!/usr/bin/env bash
# Strictly read-only streaming hash of partition prefixes. Full rootfs is 4 GiB.
set -euo pipefail
source "$(dirname "$0")/_common.sh"
usage() {
  cat <<'USAGE'
Usage: 13-verify-partition-readback.sh --boot /path/to/boot.img [--rootfs /path/to/rootfs.img]

Requires TWRP recovery ADB and root. Reads exactly image length from BOOT
and optionally USERDATA, then compares the resulting SHA-256 with local image.
No writes, formatting, mounts, reboot or flashing. --rootfs reads ~4 GiB.
USAGE
}
BOOT=""; ROOT=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --boot) [ "$#" -ge 2 ] || die '--boot requires an image'; BOOT="$2"; shift 2;;
    --rootfs) [ "$#" -ge 2 ] || die '--rootfs requires an image'; ROOT="$2"; shift 2;;
    --help|-h) usage; exit 0;;
    *) usage; die "Unexpected argument $1";;
  esac
done
[ -n "$BOOT" ] || { usage; die 'Boot image required'; }
[ -f "$BOOT" ] || die "Missing boot image: $BOOT"
[ -z "$ROOT" ] || [ -f "$ROOT" ] || die "Missing rootfs image: $ROOT"
init_out readback
require_recovery
hash_part() {
  local name="$1" device="$2" image="$3" blocksize="$4" size blocks expected actual capacity
  size="$(stat -f%z "$image" 2>/dev/null || stat -c%s "$image")"
  [ "$size" -gt 0 ] || die "$name image empty"
  [ $((size % blocksize)) -eq 0 ] || die "$name image must align to $blocksize bytes for exact readback"
  blocks=$((size / blocksize))
  capacity="$(adb_cmd shell "blockdev --getsize64 '$device'" 2>/dev/null | tr -d '\r' | tr -d '[:space:]' || true)"
  case "$capacity" in ''|*[!0-9]*) die "Cannot obtain capacity for $name";; esac
  [ "$size" -le "$capacity" ] || die "$name image exceeds partition capacity"
  expected="$(shasum -a 256 "$image" | awk '{print $1}')"
  say "Reading $name, $size bytes (~$((size/1048576)) MiB). Might take minutes."
  # pipefail propagates ADB/readback errors; hashes alone are not enough.
  actual="$(adb_cmd exec-out "dd if='$device' bs=$blocksize count=$blocks 2>/dev/null" | shasum -a 256 | awk '{print $1}')" || die "ADB readback failed for $name"
  printf '%s\texpected=%s\tactual=%s\n' "$name" "$expected" "$actual" | tee -a "$NUXEL_OUT/READBACK-HASHES.tsv"
  [ "$actual" = "$expected" ] || die "$name hash mismatch; do NOT reboot into Nuxel"
  say "$name READBACK MATCH"
}
hash_part BOOT /dev/block/by-name/boot "$BOOT" 2048
if [ -n "$ROOT" ]; then hash_part USERDATA /dev/block/by-name/userdata "$ROOT" 1048576; fi
say 'Hash matches prove stored bytes; they do not prove kernel, systemd or display boot.'
