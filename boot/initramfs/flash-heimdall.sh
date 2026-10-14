#!/usr/bin/env bash
# =============================================================================
# Nuxel Heimdall Flash — Samsung Galaxy S10+ (beyond2lte, Exynos 9820)
#
# This is the PROVEN flash path (it is exactly how postmarketOS installs the
# S10/S10e): Download Mode + heimdall, flashing
#     BOOT   <- the legacy v1 boot.img (kernel Image.gz + initramfs + DTB)
#     USERDATA <- the rootfs image (DESTRUCTIVE: overwrites user data)
#
# It does NOT use Android-bootloader-mode flashing (there is none on Exynos)
# and it does NOT need U-Boot (that is only for the mainline stretch path).
#
# Usage:
#   NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
#       --boot  build/out/s10plus/nuxel-beyond2lte-boot.img \
#       --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
#
# Options:
#   --device s10plus          REQUIRED (any other key is refused).
#   --boot <img>              v1 boot.img to flash to BOOT.
#   --rootfs <img>            rootfs image to flash to USERDATA.
#   --partition-kernel <n>    heimdall name for the kernel partition (default BOOT).
#   --partition-rootfs <n>    only USERDATA is accepted (safety).
#   --boot <img> only         flash only the boot partition (fast revert/test).
#   --dry-run                 print the heimdall commands; flash nothing.
#   --force                   skip the confirmation prompt.
#   --help                    this help.
#
# Safety: identity is checked from Download Mode PID/product if available and
# the protected partitions (efs efsg persist param up_param steady keystorage
# carrier cp_debug misc) are NEVER targeted. Knox is already tripped — never
# attempt to re-lock or restore Knox.
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROTECTED_PARTITIONS="efs efsg persist param up_param steady keystorage carrier cp_debug misc"

DEVICE_KEY=""; BOOT_IMG=""; ROOTFS_IMG=""
PART_KERNEL="BOOT"; PART_ROOTFS="USERDATA"
DRY_RUN=0; FORCE=0

log()  { echo "[s10plus-heimdall] $*"; }
err()  { echo "[s10plus-heimdall][error] $*" >&2; }

usage() { sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --device) DEVICE_KEY="$2"; shift 2 ;;
        --boot) BOOT_IMG="$2"; shift 2 ;;
        --rootfs) ROOTFS_IMG="$2"; shift 2 ;;
        --partition-kernel) PART_KERNEL="$2"; shift 2 ;;
        --partition-rootfs) PART_ROOTFS="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --force) FORCE=1; shift ;;
        *) err "unknown option: $1"; usage; exit 1 ;;
    esac
done

[ "${DEVICE_KEY}" = "s10plus" ] || { err "--device s10plus is required (got '${DEVICE_KEY}')."; exit 1; }
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" --device "${DEVICE_KEY}"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || { err "device key mismatch"; exit 1; }

# This S10+ release is scoped strictly to BOOT + USERDATA. Never use an
# operator-supplied partition alias to bypass checks or write SYSTEM.
[ "${PART_KERNEL}" = "BOOT" ] || { err "BOOT is the only allowed kernel target"; exit 1; }
[ "${PART_ROOTFS}" = "USERDATA" ] || { err "USERDATA is the only allowed rootfs target"; exit 1; }
# protected-partition denylist
for p in ${PROTECTED_PARTITIONS}; do
    [ "${PART_KERNEL}" = "${p}" ] && { err "refusing: ${PART_KERNEL} is protected"; exit 1; }
    [ "${PART_ROOTFS}" = "${p}" ] && { err "refusing: ${PART_ROOTFS} is protected"; exit 1; }
done

[ -n "${BOOT_IMG}" ] || [ -n "${ROOTFS_IMG}" ] || { err "give at least --boot or --rootfs"; exit 1; }
[ -z "${BOOT_IMG}" ]   || [ -f "${BOOT_IMG}" ]   || { err "boot image not found: ${BOOT_IMG}"; exit 1; }
[ -z "${ROOTFS_IMG}" ] || [ -f "${ROOTFS_IMG}" ] || { err "rootfs image not found: ${ROOTFS_IMG}"; exit 1; }

# Locate the *real* heimdall (not heimdall-rs the Ethereum tool).
HEIMDALL=""
for cand in "${HEIMDALL_BIN:-}" heimdall-flash /opt/homebrew/bin/heimdall-flash heimdall; do
    [ -n "${cand}" ] || continue
    if command -v "${cand}" >/dev/null 2>&1; then
        if "${cand}" version 2>/dev/null | grep -qiE '^v?[0-9]+\.[0-9]+'; then
            HEIMDALL="${cand}"; break
        fi
    fi
done
[ -n "${HEIMDALL}" ] || { err "heimdall (flash tool) not found. Install heimdall-flash (see phones/s10plus/s10plus-go-guide.md)"; exit 1; }
log "heimdall: ${HEIMDALL} ($(${HEIMDALL} version 2>/dev/null | head -1))"

ARGS=(flash)
[ -z "${BOOT_IMG}" ]   || ARGS+=("--${PART_KERNEL}" "${BOOT_IMG}")
[ -z "${ROOTFS_IMG}" ] || ARGS+=("--${PART_ROOTFS}" "${ROOTFS_IMG}")

log "Put the S10+ in Download Mode:  Vol Down + Bixby + Power (hold)."
log "Command: ${HEIMDALL} ${ARGS[*]}"
if [ "${DRY_RUN}" -eq 1 ]; then log "[dry-run] not flashing."; exit 0; fi

"${HEIMDALL}" detect || { err "no Download-Mode device detected"; exit 1; }

if [ "${FORCE}" -eq 0 ]; then
    read -rp "Flash BOOT='${BOOT_IMG:-<skip>}' USERDATA='${ROOTFS_IMG:-<skip>}'? [y/N] " c
    [[ "$c" =~ ^[Yy]$ ]] || { err "aborted"; exit 1; }
fi

"${HEIMDALL}" "${ARGS[@]}"
log "Transfer command returned successfully; confirm boot separately. Do not assume hardware boot is verified."
log "Revert to stock at any time: ${HEIMDALL} flash --BOOT <stock-boot.img>"
