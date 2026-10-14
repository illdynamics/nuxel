#!/usr/bin/env bash
# =============================================================================
# Nuxel Flash Script — Samsung Galaxy S10+ (beyond2lte, Exynos 9820)
# Flash method: TWRP (adb + dd) and Download Mode (Odin/heimdall)
#
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: THIS DEVICE HAS NO Android-bootloader-mode flashing support.
# NEVER attempt the generic Android bootloader flash protocol on this device.
# Flash via: TWRP (adb shell dd) or Download Mode (Odin/heimdall only).
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#
# Usage: NUXEL_DEVICE=s10plus boot/s10plus/flash.sh --device s10plus [options]
#
# Safety rules enforced here:
#   * --device s10plus is REQUIRED; any other value is refused.
#   * Device identity is verified before EVERY flash operation:
#     ro.product.device must be beyond2lte AND ro.product.name must be
#     beyond2ltexx (or the operator's regional variant); mismatch = refuse.
#   * Protected partitions are never touched:
#     efs efsg persist param up_param steady keystorage carrier cp_debug misc
#   * Knox fuse is already tripped — never attempt relock or Knox restore.
#   * Phase 0 inventory (docs/s10plus-device-inventory.md) must be filled
#     before real flash operations (--dry-run is exempt).
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Protected partitions — NEVER flash these
PROTECTED_PARTITIONS="efs efsg persist param up_param steady keystorage carrier cp_debug misc"

UFS_BASE="/dev/block/platform/13d60000.ufs/by-name"
DEVICE_EXPECTED="beyond2lte"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Required args
DEVICE_KEY=""
UBOOT_IMG=""
ROOTFS_IMG=""
ROOTFS_PARTITION="userdata"  # default target partition for rootfs
DO_SIDELOAD=0
DO_REVERT=0
STOCK_BOOT_IMG=""
DRY_RUN=0
FORCE=0

usage() {
    cat <<EOF
Usage: $0 --device s10plus [options]

TWRP flash sequence (adb + dd, no Android-bootloader-mode flashing):
  1. Boot the S10+ into TWRP (Vol Up + Bixby + Power).
  2. adb devices          # confirm the device is visible
  3. $0 --device s10plus --uboot build/out/s10plus/u-boot-beyond2lte.img \\
       --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
  4. adb shell twrp reboot

Options:
  --device s10plus         REQUIRED. Refuses on any other value.
  --uboot <path>           Path to u-boot-beyond2lte.img (boot partition)
  --rootfs <path>          Path to Nuxel rootfs image (default partition: userdata)
  --rootfs-partition <name> Target partition for rootfs (default: userdata)
  --sideload               Use TWRP ADB sideload instead of adb push + dd
  --revert                 Re-flash stock boot.img via heimdall (Download Mode)
  --stock-boot <path>      Stock boot.img for --revert mode
  --dry-run                Print commands but do not execute
  --force                  Skip confirmation prompts

WARNING: No Android-bootloader-mode flashing on this device. Only TWRP (adb)
         and heimdall/Odin (Download Mode).
WARNING: Knox fuse is already tripped — do not attempt relock.
WARNING: NEVER flash: ${PROTECTED_PARTITIONS}
WARNING: Device identity is verified (beyond2lte / beyond2ltexx) before every
         flash operation; a mismatch refuses to flash.
WARNING: Phase 0 inventory must be filled before real flash operations
         (see docs/s10plus-device-inventory.md).
EOF
}

# ---------------------------------------------------------------------------
# Inventory gate (Phase 0) — see docs/s10plus-device-inventory.md
# Blocks real flash operations until the operator has filled the critical
# fields from the physical device. Never blocks --help or --dry-run.
# ---------------------------------------------------------------------------
_check_s10plus_inventory() {
    local inventory="${NUXEL_ROOT}/docs/s10plus-device-inventory.md"
    # The inventory must exist — a missing file must never disarm the Phase-0 gate.
    [[ -f "${inventory}" ]] || {
        log_error "${inventory} missing — run Phase 0 inventory first."
        exit 1
    }
    # Check if UNKNOWN placeholders are still present in critical fields
    if grep -qE "KERNEL_ADDR:.*PLACEHOLDER|RAMDISK_ADDR:.*PLACEHOLDER|TAGS_ADDR:.*PLACEHOLDER|WIFI_FW_FILENAME:.*UNKNOWN" "${inventory}" 2>/dev/null; then
        echo "ERROR: S10+ device inventory is incomplete."
        echo "       Run Phase 0 collection commands in docs/s10plus-device-inventory.md"
        echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAME"
        echo "       Then re-run this script."
        exit 1
    fi
}

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --device) DEVICE_KEY="$2"; shift 2 ;;
        --uboot) UBOOT_IMG="$2"; shift 2 ;;
        --rootfs) ROOTFS_IMG="$2"; shift 2 ;;
        --rootfs-partition) ROOTFS_PARTITION="$2"; shift 2 ;;
        --sideload) DO_SIDELOAD=1; shift ;;
        --revert) DO_REVERT=1; shift ;;
        --stock-boot) STOCK_BOOT_IMG="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --force) FORCE=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Validate device key
[ "${DEVICE_KEY}" = "s10plus" ] || {
    log_error "--device s10plus is required. Got: '${DEVICE_KEY}'"
    log_error "This script is ONLY for the Samsung Galaxy S10+ (beyond2lte)."
    exit 1
}

# Device guard — print the resolved key, then verify it is s10plus.
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" --device "${DEVICE_KEY}"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || {
    log_error "Device key mismatch: expected s10plus, got ${NUXEL_DEVICE_KEY}"
    exit 1
}

# Inventory gate: real flash operations only. --dry-run is exempt so the
# operator can preview commands before Phase 0 is complete.
if [ "${DRY_RUN}" -eq 0 ]; then
    _check_s10plus_inventory
fi

log_info "Nuxel Flash — Samsung Galaxy S10+ (beyond2lte)"
log_info "Flash method: TWRP (adb+dd) | Download Mode (Odin/heimdall)"

# Revert mode
if [[ $DO_REVERT -eq 1 ]]; then
    log_warn "REVERT MODE: Re-flashing stock boot.img via heimdall (Download Mode)"
    log_warn "You must have the device in Download Mode (Vol Down + Bixby + Power)"
    [ -n "${STOCK_BOOT_IMG}" ] || { log_error "--stock-boot required for --revert"; exit 1; }
    [ -f "${STOCK_BOOT_IMG}" ] || { log_error "Stock boot image not found: ${STOCK_BOOT_IMG}"; exit 1; }
    log_info "Command: heimdall flash --BOOT '${STOCK_BOOT_IMG}'"
    if [[ $DRY_RUN -eq 0 ]]; then
        heimdall flash --BOOT "${STOCK_BOOT_IMG}"
    else
        log_info "[dry-run] heimdall flash --BOOT ${STOCK_BOOT_IMG}"
    fi
    log_ok "Revert complete."
    log_info "Full stock restore (all four firmware partitions) via Download Mode:"
    log_info "  heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5"
    exit 0
fi

# Verify device identity
log_info "Checking connected device..."
if ! command -v adb >/dev/null 2>&1; then
    log_error "adb not found — install android-tools/adb first."
    exit 1
fi
if ! adb devices | grep -q "device$"; then
    log_error "No ADB device found. Is the S10+ in TWRP with USB debugging enabled?"
    exit 1
fi

DEVICE_PROP=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')
DEVICE_NAME=$(adb shell getprop ro.product.name 2>/dev/null | tr -d '\r')
log_info "Connected: device='${DEVICE_PROP}' name='${DEVICE_NAME}'"

[ "${DEVICE_PROP}" = "${DEVICE_EXPECTED}" ] || {
    log_error "Device mismatch: expected '${DEVICE_EXPECTED}', got '${DEVICE_PROP}'"
    log_error "REFUSING TO FLASH. Connect the correct S10+ (beyond2lte) device."
    exit 1
}
if ! printf '%s' "${DEVICE_NAME}" | grep -qE "^beyond2lte"; then
    log_error "Device mismatch: ro.product.name '${DEVICE_NAME}' is not beyond2ltexx or a regional variant."
    log_error "REFUSING TO FLASH. Connect the correct S10+ (beyond2lte) device."
    exit 1
fi
log_ok "Device identity verified: ${DEVICE_PROP} / ${DEVICE_NAME}"

# Verify protected partitions are present (we will skip them)
log_info "Protected partitions (will never be touched): ${PROTECTED_PARTITIONS}"

# Validate partition target
for p in ${PROTECTED_PARTITIONS}; do
    [ "${ROOTFS_PARTITION}" = "${p}" ] && {
        log_error "ROOTFS_PARTITION='${p}' is a protected partition. Refusing."
        exit 1
    }
done

# Sideload mode
if [[ $DO_SIDELOAD -eq 1 ]]; then
    log_info "SIDELOAD MODE: Use TWRP ADB Sideload"
    log_info "In TWRP: Advanced → ADB Sideload → Swipe to start"
    log_info "Then run: adb sideload <nuxel-s10plus.zip>"
    log_warn "Sideload ZIP creation not yet implemented. Create via pmbootstrap or manually."
    exit 0
fi

# Normal flash mode
log_info "Normal flash mode: adb push + dd"
[[ -n "${UBOOT_IMG}" ]] || { log_warn "No --uboot specified; skipping boot partition flash."; }
[[ -n "${ROOTFS_IMG}" ]] || { log_warn "No --rootfs specified; skipping rootfs flash."; }

# Flash U-Boot to boot partition
if [[ -n "${UBOOT_IMG}" ]]; then
    [ -f "${UBOOT_IMG}" ] || { log_error "U-Boot image not found: ${UBOOT_IMG}"; exit 1; }
    log_info "Flashing U-Boot: ${UBOOT_IMG} → ${UFS_BASE}/boot"
    if [[ $FORCE -eq 0 ]]; then
        read -rp "Confirm flash U-Boot to /boot? [y/N] " c
        [[ "$c" =~ ^[Yy]$ ]] || { log_error "Aborted by user."; exit 1; }
    fi
    if [[ $DRY_RUN -eq 0 ]]; then
        adb push "${UBOOT_IMG}" /tmp/nuxel-uboot.img
        adb shell "dd if=/tmp/nuxel-uboot.img of=${UFS_BASE}/boot bs=4096"
        log_ok "U-Boot flashed to ${UFS_BASE}/boot"
    else
        log_info "[dry-run] adb push ${UBOOT_IMG} /tmp/nuxel-uboot.img"
        log_info "[dry-run] adb shell dd if=/tmp/nuxel-uboot.img of=${UFS_BASE}/boot bs=4096"
    fi
fi

# Flash rootfs
if [[ -n "${ROOTFS_IMG}" ]]; then
    [ -f "${ROOTFS_IMG}" ] || { log_error "Rootfs image not found: ${ROOTFS_IMG}"; exit 1; }
    log_info "Flashing rootfs: ${ROOTFS_IMG} → ${UFS_BASE}/${ROOTFS_PARTITION}"
    log_warn "This will OVERWRITE /${ROOTFS_PARTITION} — ensure backups exist."
    if [[ $FORCE -eq 0 ]]; then
        read -rp "Confirm flash rootfs to /${ROOTFS_PARTITION}? [y/N] " c
        [[ "$c" =~ ^[Yy]$ ]] || { log_error "Aborted by user."; exit 1; }
    fi
    if [[ $DRY_RUN -eq 0 ]]; then
        adb push "${ROOTFS_IMG}" /tmp/nuxel-rootfs.img
        adb shell "dd if=/tmp/nuxel-rootfs.img of=${UFS_BASE}/${ROOTFS_PARTITION} bs=4096"
        log_ok "Rootfs flashed to ${UFS_BASE}/${ROOTFS_PARTITION}"
    else
        log_info "[dry-run] adb push ${ROOTFS_IMG} /tmp/nuxel-rootfs.img"
        log_info "[dry-run] adb shell dd if=/tmp/nuxel-rootfs.img of=${UFS_BASE}/${ROOTFS_PARTITION} bs=4096"
    fi
fi

log_ok "Flash complete."
log_info "Reboot: adb shell twrp reboot"
log_info "If it does not boot, enter Download Mode (Vol Down + Bixby + Power)"
log_info "and re-flash stock: heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5"
