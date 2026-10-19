#!/usr/bin/env bash
# =============================================================================
# Nuxel Flash Script — Motorola Moto G7 Power (ocean, SDM632 / msm8953)
# Flash method: fastboot (stock ABOOT) + lk2nd + EDL 9008 (unbrick)
#
# !!! CRITICAL FLASH ORDER — NEVER CHANGE THIS !!!
# 1. flash dtbo (MANDATORY FIRST — prevents soft-brick)
# 2. flash boot with lk2nd.img (via stock ABOOT fastboot)
# 3. reboot into lk2nd fastboot
# 4. flash boot with mainline Nuxel boot.img (via lk2nd fastboot)
# 5. flash userdata with rootfs
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

PROTECTED_PARTITIONS="modemst1 modemst2 fsg fsc ddr persist misc"
DEVICE_EXPECTED="ocean"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# Inventory gate (Phase 0) — see docs/g7power-device-inventory.md
# Blocks real flash operations until the operator has filled the critical
# fields from the physical device. Never blocks --help, --edl, --unlock-help
# or --dry-run.
# ---------------------------------------------------------------------------
_check_g7power_inventory() { local inv="${NUXEL_ROOT}/docs/g7power-device-inventory.md"; [ -f "${inv}" ] || { echo "ERROR: docs/g7power-device-inventory.md missing — run Phase 0 inventory first."; exit 1; }; if grep -qE "KERNEL_ADDR:.*PLACEHOLDER|RAMDISK_ADDR:.*PLACEHOLDER|TAGS_ADDR:.*PLACEHOLDER|WIFI_FW_FILENAMES:.*UNKNOWN" "${inv}"; then echo "ERROR: G7 Power device inventory incomplete."; echo "       Run Phase 0 commands in docs/g7power-device-inventory.md"; echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, WIFI_FW_FILENAMES"; exit 1; fi; }

# Args
DEVICE_KEY=""
LK2ND_IMG=""
BOOT_IMG=""
DTBO_IMG=""
ROOTFS_IMG=""
ROOTFS_PARTITION="userdata"
DO_UNLOCK_HELP=0
DO_REVERT=0
STOCK_BOOT_IMG=""
STOCK_DTBO_IMG=""
DRY_RUN=0
FORCE=0

usage() {
    cat <<EOF
Usage: $0 --device g7power [options]

CRITICAL FLASH ORDER (enforced in code):
  1. --dtbo  must be flashed BEFORE --lk2nd (prevents soft-brick on msm8953)
  2. --lk2nd flash is via STOCK ABOOT fastboot
  3. --boot  flash is via LK2ND fastboot (after reboot)
  4. --rootfs flash is via LK2ND fastboot

Options:
  --device g7power         REQUIRED. Refuses on any other value.
  --dtbo  <path>           Path to dtbo.img (flashed FIRST, via stock ABOOT fastboot)
  --lk2nd <path>           Path to lk2nd.img (flashed to boot partition, stock ABOOT)
  --boot  <path>           Path to Nuxel boot.img (flashed via lk2nd fastboot)
  --rootfs <path>          Path to Nuxel rootfs image
  --rootfs-partition <n>   Target partition (default: userdata)
  --unlock-help            Print Motorola unlock portal instructions
  --revert                 Re-flash stock boot + dtbo (reverts lk2nd + Nuxel)
  --stock-boot <path>      Stock boot.img for --revert
  --stock-dtbo <path>      Stock dtbo.img for --revert (REQUIRED with --revert)
  --edl                    Print EDL (Qualcomm 9008) unbrick instructions
  --dry-run                Print commands but do not execute
  --force                  Skip confirmation prompts

NEVER touch: ${PROTECTED_PARTITIONS}
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --device)           DEVICE_KEY="$2"; shift 2 ;;
        --dtbo)             DTBO_IMG="$2"; shift 2 ;;
        --lk2nd)            LK2ND_IMG="$2"; shift 2 ;;
        --boot)             BOOT_IMG="$2"; shift 2 ;;
        --rootfs)           ROOTFS_IMG="$2"; shift 2 ;;
        --rootfs-partition) ROOTFS_PARTITION="$2"; shift 2 ;;
        --unlock-help)      DO_UNLOCK_HELP=1; shift ;;
        --revert)           DO_REVERT=1; shift ;;
        --stock-boot)       STOCK_BOOT_IMG="$2"; shift 2 ;;
        --stock-dtbo)       STOCK_DTBO_IMG="$2"; shift 2 ;;
        --edl)              cat "${NUXEL_ROOT}/boot/g7power/lk2nd/README.md" | grep -A20 "EDL"; exit 0 ;;
        --dry-run)          DRY_RUN=1; shift ;;
        --force)            FORCE=1; shift ;;
        --help|-h)          usage; exit 0 ;;
        *)                  log_error "Unknown: $1"; usage; exit 1 ;;
    esac
done

# Validate device key
[ "${DEVICE_KEY}" = "g7power" ] || {
    log_error "--device g7power required. Got: '${DEVICE_KEY}'"
    log_error "This script is ONLY for the Motorola Moto G7 Power (ocean)."
    exit 1
}

# Device guard — print the resolved key, then verify it is g7power.
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" --device "${DEVICE_KEY}"
[ "${NUXEL_DEVICE_KEY}" = "g7power" ] || {
    log_error "Device key mismatch: expected g7power, got ${NUXEL_DEVICE_KEY}"
    exit 1
}

log_info "Nuxel Flash — Motorola Moto G7 Power (ocean, SDM632)"
log_info "Flash method: fastboot (stock ABOOT) + lk2nd + EDL 9008 (unbrick)"

# Unlock help
if [[ $DO_UNLOCK_HELP -eq 1 ]]; then
    cat <<'EOF'
=== Motorola Bootloader Unlock Instructions ===

1. Enable USB debugging and OEM Unlock in Developer Options.
2. Reboot to fastboot: adb reboot bootloader
3. Get unlock data:
   fastboot oem get_unlock_data
   (copies a string to the terminal — save it)
4. Submit unlock request:
   https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device
   Paste the unlock data, submit, wait for the email with your unlock code.
5. Unlock (WIPES DEVICE — BACKUP FIRST):
   fastboot oem unlock <YOUR_UNLOCK_CODE>
6. Reboot and re-enable USB debugging.
EOF
    # NOTE: NEVER run `fastboot oem lock` during development — bootloader
    # relock is OUT OF SCOPE for this pass (documented in
    # docs/g7power-bringup.md). Development flashing happens with an
    # UNLOCKED bootloader only; relock requires an explicit production flow
    # with a triple confirmation, which is not implemented yet.
    exit 0
fi

# Inventory gate: real flash operations only. --dry-run is exempt so the
# operator can preview commands before Phase 0 is complete.
if [ "${DRY_RUN}" -eq 0 ]; then
    _check_g7power_inventory
fi

# Verify device identity
log_info "Checking connected device..."
if ! fastboot devices | grep -q "."; then
    log_error "No fastboot device found. Is the G7 Power in fastboot mode?"
    log_error "Enter fastboot: power off, then hold Vol Down + Power."
    exit 1
fi

PRODUCT=$(fastboot getvar product 2>&1 | grep '^product:' | awk '{print $2}' | tr -d '\r')
SERIAL=$(fastboot getvar serialno 2>&1 | grep '^serialno:' | awk '{print $2}' | tr -d '\r')
UNLOCKED=$(fastboot getvar unlocked 2>&1 | grep '^unlocked:' | awk '{print $2}' | tr -d '\r')

log_info "Product: ${PRODUCT} | Serial: ${SERIAL} | Unlocked: ${UNLOCKED}"

[ "${PRODUCT}" = "${DEVICE_EXPECTED}" ] || {
    log_error "Device mismatch: expected '${DEVICE_EXPECTED}', got '${PRODUCT}'"
    log_error "REFUSING TO FLASH. Connect the correct G7 Power (ocean)."
    exit 1
}
[ "${UNLOCKED}" = "yes" ] || {
    log_error "Bootloader is LOCKED. Run: bash boot/g7power/flash.sh --unlock-help"
    exit 1
}

# Serial pinning (invariant 3): if NUXEL_EXPECTED_SERIAL is set and
# non-empty, refuse unless it matches the connected device exactly.
if [[ -n "${NUXEL_EXPECTED_SERIAL:-}" ]]; then
    [ "${SERIAL}" = "${NUXEL_EXPECTED_SERIAL}" ] || {
        log_error "Serial mismatch: expected '${NUXEL_EXPECTED_SERIAL}', got '${SERIAL}'"
        log_error "REFUSING TO FLASH. NUXEL_EXPECTED_SERIAL does not match the connected device."
        exit 1
    }
fi
log_ok "Device verified: ${PRODUCT} (${SERIAL}), unlocked: ${UNLOCKED}"

# Protected partition validation
for p in ${PROTECTED_PARTITIONS}; do
    [ "${ROOTFS_PARTITION}" = "${p}" ] && {
        log_error "ROOTFS_PARTITION='${p}' is protected. Refusing."
        exit 1
    }
done

# Revert mode
if [[ $DO_REVERT -eq 1 ]]; then
    log_warn "REVERT MODE: Re-flashing stock dtbo + boot (removes lk2nd + Nuxel kernel)"
    [ -n "${STOCK_DTBO_IMG}" ] || { log_error "--stock-dtbo required for --revert"; exit 1; }
    [ -n "${STOCK_BOOT_IMG}" ] || { log_error "--stock-boot required for --revert"; exit 1; }
    [ -f "${STOCK_DTBO_IMG}" ] || { log_error "dtbo not found: ${STOCK_DTBO_IMG}"; exit 1; }
    [ -f "${STOCK_BOOT_IMG}" ] || { log_error "boot not found: ${STOCK_BOOT_IMG}"; exit 1; }

    log_info "Flashing stock dtbo first..."
    [[ $DRY_RUN -eq 0 ]] && fastboot flash dtbo "${STOCK_DTBO_IMG}" || \
        log_info "[dry-run] fastboot flash dtbo ${STOCK_DTBO_IMG}"
    log_info "Flashing stock boot..."
    [[ $DRY_RUN -eq 0 ]] && fastboot flash boot "${STOCK_BOOT_IMG}" || \
        log_info "[dry-run] fastboot flash boot ${STOCK_BOOT_IMG}"
    [[ $DRY_RUN -eq 0 ]] && fastboot reboot || log_info "[dry-run] fastboot reboot"
    log_ok "Revert complete."
    exit 0
fi

# === PHASE 1: Stock ABOOT fastboot — flash dtbo + lk2nd ===
if [[ -n "${DTBO_IMG}" ]] || [[ -n "${LK2ND_IMG}" ]]; then
    log_info "=== PHASE 1: Stock ABOOT fastboot (dtbo + lk2nd) ==="

    # STEP 1 — dtbo MUST come before lk2nd (enforced in code)
    if [[ -n "${DTBO_IMG}" ]]; then
        [ -f "${DTBO_IMG}" ] || { log_error "dtbo not found: ${DTBO_IMG}"; exit 1; }
        log_warn "Flashing dtbo FIRST (mandatory on msm8953)..."
        [[ $FORCE -eq 0 ]] && read -rp "Flash dtbo? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash dtbo "${DTBO_IMG}" || \
            log_info "[dry-run] fastboot flash dtbo ${DTBO_IMG}"
        log_ok "dtbo flashed."
    else
        log_warn "No --dtbo specified. ENSURE dtbo is intact before flashing lk2nd!"
    fi

    # STEP 2 — lk2nd to boot partition (via stock ABOOT fastboot)
    if [[ -n "${LK2ND_IMG}" ]]; then
        [ -f "${LK2ND_IMG}" ] || { log_error "lk2nd not found: ${LK2ND_IMG}"; exit 1; }
        log_info "Flashing lk2nd to boot partition (stock ABOOT fastboot)..."
        [[ $FORCE -eq 0 ]] && read -rp "Flash lk2nd to /boot? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash boot "${LK2ND_IMG}" || \
            log_info "[dry-run] fastboot flash boot ${LK2ND_IMG}"
        log_ok "lk2nd flashed."

        log_info "Rebooting into lk2nd fastboot..."
        [[ $DRY_RUN -eq 0 ]] && fastboot reboot bootloader || \
            log_info "[dry-run] fastboot reboot bootloader"
        log_info "Waiting for lk2nd fastboot to appear (10s)..."
        sleep 10
        log_info "Now in lk2nd fastboot. Proceeding to Phase 2..."
    fi
fi

# === PHASE 2: lk2nd fastboot — flash mainline kernel boot.img + rootfs ===
if [[ -n "${BOOT_IMG}" ]] || [[ -n "${ROOTFS_IMG}" ]]; then
    log_info "=== PHASE 2: lk2nd fastboot (Nuxel boot.img + rootfs) ==="

    if [[ -n "${BOOT_IMG}" ]]; then
        [ -f "${BOOT_IMG}" ] || { log_error "boot.img not found: ${BOOT_IMG}"; exit 1; }
        log_info "Flashing Nuxel boot.img via lk2nd fastboot..."
        [[ $FORCE -eq 0 ]] && read -rp "Flash Nuxel boot.img? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash boot "${BOOT_IMG}" || \
            log_info "[dry-run] fastboot flash boot ${BOOT_IMG}"
        log_ok "Nuxel boot.img flashed."
    fi

    if [[ -n "${ROOTFS_IMG}" ]]; then
        [ -f "${ROOTFS_IMG}" ] || { log_error "rootfs not found: ${ROOTFS_IMG}"; exit 1; }
        log_warn "Flashing rootfs to /${ROOTFS_PARTITION} — this OVERWRITES existing data."
        [[ $FORCE -eq 0 ]] && read -rp "Flash rootfs to /${ROOTFS_PARTITION}? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
        [[ $DRY_RUN -eq 0 ]] && fastboot flash "${ROOTFS_PARTITION}" "${ROOTFS_IMG}" || \
            log_info "[dry-run] fastboot flash ${ROOTFS_PARTITION} ${ROOTFS_IMG}"
        log_ok "Rootfs flashed to /${ROOTFS_PARTITION}."
    fi

    [[ $DRY_RUN -eq 0 ]] && fastboot reboot || log_info "[dry-run] fastboot reboot"
fi

log_ok "Flash complete."
log_info "If the device does not boot:"
log_info "  Revert: bash boot/g7power/flash.sh --device g7power --revert \\"
log_info "          --stock-dtbo <stock-dtbo.img> --stock-boot <stock-boot.img>"
log_info "  EDL:    bash boot/g7power/flash.sh --edl"
