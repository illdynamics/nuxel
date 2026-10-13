#!/usr/bin/env bash
# =============================================================================
# Nuxel Recovery Helper — Samsung Galaxy S10+ (beyond2lte, Exynos 9820)
#
# The S10+ (Exynos) recovery model:
#   * TWRP is the only on-device recovery environment (Vol Up + Bixby + Power).
#   * Download Mode (Vol Down + Bixby + Power) + Odin/heimdall is the only
#     host-driven full-stock restore path.
#   * There is NO vendor "Android bootloader flash protocol" recovery path on
#     Exynos — do not look for one, do not try to use one.
#
# This helper only prints instructions and the exact heimdall commands; it
# never flashes anything by itself and never touches the protected partitions
# (efs efsg persist param up_param steady keystorage carrier cp_debug misc).
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BOOT_CONFIG="${NUXEL_ROOT}/boot/s10plus/boot-config.txt"

PROTECTED_PARTITIONS="efs efsg persist param up_param steady keystorage carrier cp_debug misc"

log()  { echo "[recovery-s10plus] $*"; }

usage() {
    cat <<EOF
Usage: boot/s10plus/recovery.sh [--help]

S10+ recovery reference (Samsung Galaxy S10+, beyond2lte, Exynos 9820).
Machine-readable boot facts: ${BOOT_CONFIG}

Key combos:
  Download Mode   Vol Down + Bixby + Power   (hold until the warning screen)
  TWRP            Vol Up   + Bixby + Power   (hold until TWRP starts)

Full stock restore (Download Mode + heimdall, four firmware partitions):
  heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5

  BL, AP, CP, CSC come from the Samsung stock firmware tarball for SM-G975F
  (Odin package). Extract the four .tar.md5 files and point heimdall at them.
  WARNING: never flash a CSC/AP for a different regional variant, and never
  attempt to relock the bootloader or restore Knox (Knox fuse is already
  tripped; ODIN LOCK may brick the device).

Stock boot partition restore (single partition, Download Mode):
  heimdall flash --BOOT <stock-boot.img>

TWRP re-flash via ADB sideload:
  1. Boot TWRP (Vol Up + Bixby + Power)
  2. TWRP: Advanced -> ADB Sideload -> Swipe to start
  3. adb sideload twrp-beyond2lte.zip   (or nuxel-s10plus.zip)

There is NO vendor Android-bootloader-mode (vendor unlock) recovery path
on this Exynos device. Recovery is TWRP + Download Mode (Odin/heimdall) only.
The protected partitions are never flashed: ${PROTECTED_PARTITIONS}
EOF
}

for arg in "$@"; do
    case "$arg" in
        --help|-h) usage; exit 0 ;;
        *) log "Unknown option: $arg"; usage; exit 1 ;;
    esac
done

usage
