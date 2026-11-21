#!/usr/bin/env bash
# =============================================================================
# NUXEL S10+ EMERGENCY RECOVERY — flash the matched known-good image set.
#
# Recovery artifacts (all SHA-256 verified, see NUXEL_KNOWN_GOOD_BOOT_IMAGES.md):
#   dtb-sda12.img            8,388,608 B  -> Download Mode name: DTB  (sda12)
#   dtbo-sda13.img           8,388,608 B  -> Download Mode name: DTBO (sda13)
#   nuxel-boot-known-good.img 48,146,432 B -> Download Mode name: BOOT (sda14)
#
# TWO supported paths:
#   A) Download Mode (RECOMMENDED):   bash flash-recovery.sh --heimdall
#   B) TWRP (adb + dd):               bash flash-recovery.sh --twrp
#
# SAFETY: this flashes ONLY the three boot-chain partitions (DTB/DTBO/BOOT).
# It does NOT touch efs/param/vbmeta/recovery/userdata or any protected partition.
# It does NOT repartition and does NOT modify the PIT.
# =============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UFS="/dev/block/platform/13d60000.ufs/by-name"

DTB="${HERE}/dtb-sda12.img"
DTBO="${HERE}/dtbo-sda13.img"
BOOT="${HERE}/nuxel-boot-known-good.img"

verify_sha() {
  local f="$1" want="$2"
  local got
  got="$(shasum -a 256 "$f" | awk '{print $1}')"
  [ "$got" = "$want" ] || { echo "SHA-256 MISMATCH for $f"; echo "  want $want"; echo "  got  $got"; exit 1; }
}
verify_sha "$DTB"  699208ba2086df8c64d93ceb68b0201f6ec192a25686128ab8c3b446d3c16c7c
verify_sha "$DTBO" fa93e41d8b2a1693b9e3f155264db7ea77c6fd37ca5b66d81f5472d580d425fb
verify_sha "$BOOT" 8fe74777950b4bfbd56d8459ef06cfd37f8445ca772fb611ae9c1bc34d1bd859

MODE="${1:-}"
case "$MODE" in
  --heimdall)
    echo "==> Download Mode heimdall flash (DTB + DTBO + BOOT as a matched set)"
    echo "    Verify the phone is in Download Mode (Vol Down + Bixby + Power)."
    heimdall detect || { echo "No Download-Mode device detected."; exit 1; }
    heimdall flash --DTB "$DTB" --DTBO "$DTBO" --BOOT "$BOOT"
    echo "==> Flash complete. Reboot and observe boot. Do not interrupt."
    ;;
  --twrp)
    echo "==> TWRP adb + dd flash (sda12 + sda13 + sda14)"
    adb devices | grep -q "recovery" || { echo "No TWRP (recovery) adb device."; echo "Boot TWRP: Vol Up + Bixby + Power. Enable adb."; exit 1; }
    for spec in "dtb:${DTB}:/nuxel-dtb.img:sda12" "dtbo:${DTBO}:/nuxel-dtbo.img:sda13" "boot:${BOOT}:/nuxel-boot.img:sda14"; do
      part="${spec%%:*}"; rest="${spec#*:}"; local="${rest%%:*}"; rest="${rest#*:}"; remote="${rest%%:*}"; sd="${rest#*:}"
      echo "  flashing $part -> $UFS/$part (${sd})"
      adb push "$local" "$remote"
      adb shell "dd if=$remote of=${UFS}/${part} bs=4096" && echo "  $part written"
      adb shell "sync"
    done
    echo "==> Flash complete. adb shell twrp reboot"
    ;;
  *)
    echo "Usage: $0 [--heimdall|--twrp]"
    exit 1
    ;;
esac
