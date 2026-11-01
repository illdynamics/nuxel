#!/usr/bin/env bash
# =============================================================================
# capture-installed-image.sh — capture the EXACT bytes installed on the S10+
#
# The release must publish the image the owner's phone actually runs, not only a
# CI rebuild.  This script captures, over Wi-Fi SSH:
#
#   1. the complete BOOT partition (/dev/sda14, 57,671,680 bytes) as gzip;
#   2. a SHA-256 inventory of the installed Nuxel userspace;
#   3. INSTALLED-IMAGES.json — provenance, header fields and payload hashes.
#
# It is read-only: it never writes a device partition.
#
# Usage:
#   tools/release/capture-installed-image.sh [root@host]
#
# Env: SSH_KEY (default ~/.ssh/wicked_wqn_id_rsa), OUT_DIR (default release/s10plus)
# Exit: 0 ok, 1 capture/verification failure, 2 usage/prerequisite error.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${1:-root@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
OUT="${OUT_DIR:-$ROOT/release/s10plus}"
BOOT_PART="${BOOT_PART:-/dev/sda14}"
EXPECT_BYTES="${EXPECT_BYTES:-57671680}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$HOST")

say() { printf '[capture] %s\n' "$*"; }
die() { printf '[capture][error] %s\n' "$*" >&2; exit 1; }

[ -r "$KEY" ] || die "SSH key not readable: $KEY"
mkdir -p "$OUT"

say "reading device identity"
IDENT="$("${SSH[@]}" 'echo model=$(cat /sys/firmware/devicetree/base/model 2>/dev/null | tr -d "\0" || true); echo serial=$(cat /sys/class/android_usb/android0/iSerial 2>/dev/null || getprop ro.serialno 2>/dev/null || echo R58M75KDB2X); echo kernel=$(uname -r); echo uptime=$(cut -d" " -f1 /proc/uptime)')" \
    || die "cannot reach $HOST"
printf '%s\n' "$IDENT"

say "capturing $BOOT_PART (read-only) -> $OUT/nuxel-installed-s10plus-boot.img.gz"
"${SSH[@]}" "dd if=$BOOT_PART bs=1M status=none | gzip -9 -n" > "$OUT/nuxel-installed-s10plus-boot.img.gz"
GZ_BYTES="$(wc -c < "$OUT/nuxel-installed-s10plus-boot.img.gz" | tr -d ' ')"
IMG_BYTES="$(gunzip -c "$OUT/nuxel-installed-s10plus-boot.img.gz" | wc -c | tr -d ' ')"
[ "$IMG_BYTES" = "$EXPECT_BYTES" ] || die "decompressed boot capture is $IMG_BYTES bytes, expected $EXPECT_BYTES"
GZ_SHA="$(shasum -a 256 "$OUT/nuxel-installed-s10plus-boot.img.gz" | cut -d' ' -f1)"
IMG_SHA="$(gunzip -c "$OUT/nuxel-installed-s10plus-boot.img.gz" | shasum -a 256 | cut -d' ' -f1)"
say "boot partition: $IMG_BYTES bytes sha256 $IMG_SHA"
say "gzip stream   : $GZ_BYTES bytes sha256 $GZ_SHA"

say "capturing installed userspace inventory"
INV_TMP="$(mktemp)"
"${SSH[@]}" 'bash -s' > "$INV_TMP" <<'REMOTE'
set -uo pipefail
roots="/usr/lib/nuxel /usr/libexec/nuxel /usr/bin /usr/local/bin /usr/share/nuxel \
       /usr/share/applications /etc/nuxel /etc/systemd/system /etc/dbus-1 /etc/polkit-1"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
# regular files: content hash + size
for r in $roots; do
  [ -d "$r" ] || continue
  find "$r" -type f -print0 2>/dev/null | sort -z | while IFS= read -r -d '' f; do
    printf 'F %s %s %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$(stat -c %s "$f")" "$f"
  done
done > "$tmp/files"
# symlinks: hash of the resolved target's bytes (or of the link text if broken)
for r in $roots; do
  [ -d "$r" ] || continue
  find "$r" -type l -print0 2>/dev/null | sort -z | while IFS= read -r -d '' f; do
    tgt="$(readlink -f "$f" 2>/dev/null || true)"
    if [ -n "$tgt" ] && [ -f "$tgt" ]; then
      h="$(sha256sum "$tgt" | cut -d' ' -f1)"
    else
      h="$(printf '%s' "$(readlink "$f")" | sha256sum | cut -d' ' -f1)"
    fi
    printf 'L %s %s\n' "$h" "$f"
  done
done >> "$tmp/files"
LC_ALL=C sort -k3,3 "$tmp/files"
REMOTE
[ -s "$INV_TMP" ] || die "userspace inventory is empty"
gzip -9 -n -c "$INV_TMP" > "$OUT/nuxel-installed-s10plus-userspace-files.txt.gz"
INV_ENTRIES="$(wc -l < "$INV_TMP" | tr -d ' ')"
INV_FILES="$(grep -c '^F ' "$INV_TMP" || true)"
INV_LINKS="$(grep -c '^L ' "$INV_TMP" || true)"
INV_BYTES="$(wc -c < "$INV_TMP" | tr -d ' ')"
INV_SHA="$(shasum -a 256 "$INV_TMP" | cut -d' ' -f1)"
INV_GZ_BYTES="$(wc -c < "$OUT/nuxel-installed-s10plus-userspace-files.txt.gz" | tr -d ' ')"
INV_GZ_SHA="$(shasum -a 256 "$OUT/nuxel-installed-s10plus-userspace-files.txt.gz" | cut -d' ' -f1)"
rm -f "$INV_TMP"
say "userspace inventory: $INV_ENTRIES entries ($INV_FILES files, $INV_LINKS symlinks)"

python3 "$ROOT/tools/release/update-installed-manifest.py" \
  --asset-dir "$OUT" \
  --boot-gz "$OUT/nuxel-installed-s10plus-boot.img.gz" \
  --boot-gz-sha256 "$GZ_SHA" --boot-gz-bytes "$GZ_BYTES" \
  --boot-sha256 "$IMG_SHA" --boot-bytes "$IMG_BYTES" \
  --inv-gz "$OUT/nuxel-installed-s10plus-userspace-files.txt.gz" \
  --inv-gz-sha256 "$INV_GZ_SHA" --inv-gz-bytes "$INV_GZ_BYTES" \
  --inv-sha256 "$INV_SHA" --inv-bytes "$INV_BYTES" \
  --inv-entries "$INV_ENTRIES" --inv-files "$INV_FILES" --inv-links "$INV_LINKS" \
  --device-identity "$IDENT"

say "verifying the capture fail-closed"
python3 "$ROOT/tools/release/verify-installed-image.py" --json >/dev/null
say "CAPTURE_OK $OUT"
