#!/usr/bin/env bash
# Clones, builds, and flashes chiffathefox/u-boot (exynos9820) to the S10+.
# Device must be in TWRP (adb connected).
# NEVER uses Android-bootloader-mode flashing — flash path is TWRP adb+dd and
# Download Mode (Odin/heimdall) only.
#
# Usage:
#   NUXEL_DEVICE=s10plus bash boot/s10plus/uboot-chainload.sh [--device s10plus]
#   --help  print this help and exit (runs offline)
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

UBOOT_REPO="https://github.com/chiffathefox/u-boot"
UBOOT_BRANCH="exynos9820"
UBOOT_BUILD_DIR="${NUXEL_ROOT}/kernel/s10plus/.build/u-boot"
CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
CC="${CC:-aarch64-linux-gnu-gcc-10}"

UFS_BASE="/dev/block/platform/13d60000.ufs/by-name"
UFS_BOOT="${UFS_BASE}/boot"

# Protected partitions — NEVER flash these
PROTECTED_PARTITIONS="efs efsg persist param up_param steady keystorage carrier cp_debug misc"

usage() {
    cat <<'HELP'
Usage: NUXEL_DEVICE=s10plus boot/s10plus/uboot-chainload.sh [--device s10plus]

Clones, builds, and flashes chiffathefox/u-boot (exynos9820) to the S10+.
Device must be in TWRP (adb connected). Flash path: TWRP adb+dd and Download
Mode (Odin/heimdall) only.

Options:
  --device <key>   Device key (s10plus or alias beyond2lte). Defaults to the
                   NUXEL_DEVICE environment variable.
  --help, -h       Print this help and exit (runs offline).

Safety: identity is verified (ro.product.device=beyond2lte AND
ro.product.name=beyond2ltexx or regional variant) before any device
operation; the protected partitions
(efs efsg persist param up_param steady keystorage carrier cp_debug misc)
are never touched; the flash target is the UFS by-name boot partition only.
HELP
}

for arg in "$@"; do
    case "$arg" in
        --help|-h) usage; exit 0 ;;
    esac
done

# Device guard — S10+ only. Explicit selection required (env or --device).
# Sourced BEFORE any work message: the resolved device key is printed first
# and a wrong/missing device key aborts before any build/flash output.
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || {
    echo "ERROR: boot/s10plus/uboot-chainload.sh is ONLY for s10plus. Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

echo "[uboot-chainload] Building chiffathefox/u-boot for Exynos 9820..."

# ---------------------------------------------------------------------------
# Inventory gate (Phase 0) — see docs/s10plus-device-inventory.md
# Blocks real flash operations until the operator has filled the critical
# fields from the physical device. Never blocks --help (handled above).
# ---------------------------------------------------------------------------
_check_s10plus_inventory() {
    local inventory="${NUXEL_ROOT}/docs/s10plus-device-inventory.md"
    # The inventory must exist — a missing file must never disarm the Phase-0 gate.
    [[ -f "${inventory}" ]] || {
        echo "ERROR: ${inventory} missing — run Phase 0 inventory first."
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
_check_s10plus_inventory

# Verify S10+ connected in TWRP
if ! command -v adb >/dev/null 2>&1; then
    echo "ERROR: adb not found — install android-tools/adb first."
    exit 1
fi
if ! adb devices | grep -q "device$"; then
    echo "ERROR: No ADB device found. Connect the S10+ in TWRP first."
    exit 1
fi
DEVICE_PROP=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')
DEVICE_NAME=$(adb shell getprop ro.product.name 2>/dev/null | tr -d '\r')
[ "${DEVICE_PROP}" = "beyond2lte" ] || {
    echo "ERROR: Expected ro.product.device=beyond2lte, got '${DEVICE_PROP}'. Connect S10+ in TWRP first."
    exit 1
}
if ! printf '%s' "${DEVICE_NAME}" | grep -qE "^beyond2lte"; then
    echo "ERROR: Expected ro.product.name beyond2ltexx (or regional variant), got '${DEVICE_NAME}'."
    echo "       REFUSING to flash a different device."
    exit 1
fi
echo "[uboot-chainload] Identity verified: ${DEVICE_PROP} / ${DEVICE_NAME}."

# Denylist check — the dd target must never be a protected partition
for p in ${PROTECTED_PARTITIONS}; do
    case "${UFS_BOOT}" in
        "${UFS_BASE}/${p}") echo "ERROR: ${UFS_BOOT} is a protected partition. Refusing."; exit 1 ;;
    esac
done

# Clone U-Boot
if [[ ! -d "${UBOOT_BUILD_DIR}/.git" ]]; then
    git clone --depth=1 -b "${UBOOT_BRANCH}" "${UBOOT_REPO}" "${UBOOT_BUILD_DIR}"
fi

# Build
cd "${UBOOT_BUILD_DIR}"
make CC="${CC}" CROSS_COMPILE="${CROSS_COMPILE}" exynos9820_defconfig
make CC="${CC}" CROSS_COMPILE="${CROSS_COMPILE}" -j"$(nproc)"

# Phase-0 inventory load addresses: the gate above guarantees the fields are
# filled, so feed the inventoried (device-derived) values to the packer —
# otherwise every post-inventory build would silently use the packer's
# PLACEHOLDER defaults.
INVENTORY="${NUXEL_ROOT}/docs/s10plus-device-inventory.md"
INV_ADDR_KERNEL="$(awk '/^KERNEL_ADDR:/{print $2; exit}' "${INVENTORY}")"
INV_ADDR_RAMDISK="$(awk '/^RAMDISK_ADDR:/{print $2; exit}' "${INVENTORY}")"
INV_ADDR_TAGS="$(awk '/^TAGS_ADDR:/{print $2; exit}' "${INVENTORY}")"
PACK_ADDR_ARGS=()
if [[ "${INV_ADDR_KERNEL}" =~ ^0x[0-9a-fA-F]+$ ]]; then
    PACK_ADDR_ARGS+=(--kernel-addr "${INV_ADDR_KERNEL}")
else
    echo "[uboot-chainload] WARNING: KERNEL_ADDR ('${INV_ADDR_KERNEL}') is not a hex address in ${INVENTORY}; using packer default."
fi
if [[ "${INV_ADDR_RAMDISK}" =~ ^0x[0-9a-fA-F]+$ ]]; then
    PACK_ADDR_ARGS+=(--ramdisk-addr "${INV_ADDR_RAMDISK}")
else
    echo "[uboot-chainload] WARNING: RAMDISK_ADDR ('${INV_ADDR_RAMDISK}') is not a hex address in ${INVENTORY}; using packer default."
fi
if [[ "${INV_ADDR_TAGS}" =~ ^0x[0-9a-fA-F]+$ ]]; then
    PACK_ADDR_ARGS+=(--tags-addr "${INV_ADDR_TAGS}")
else
    echo "[uboot-chainload] WARNING: TAGS_ADDR ('${INV_ADDR_TAGS}') is not a hex address in ${INVENTORY}; using packer default."
fi
if [ ${#PACK_ADDR_ARGS[@]} -eq 0 ]; then
    echo "[uboot-chainload] ERROR: no real load addresses from ${INVENTORY} — refusing to pack/flash u-boot-beyond2lte.img with the packer PLACEHOLDER defaults."
    echo "[uboot-chainload] Fill KERNEL_ADDR/RAMDISK_ADDR/TAGS_ADDR from the real device stock boot.img before flashing."
    exit 1
fi

# Wrap u-boot.bin as a legacy v1 boot image for S-Boot
# S-Boot reads boot.img format; we wrap u-boot.bin as the "kernel"
# (path is NUXEL_ROOT-based so the wrapper works regardless of cwd)
python3 "${NUXEL_ROOT}/boot/s10plus/pack-boot-v1.sh" \
    --kernel u-boot.bin \
    --ramdisk /dev/null \
    --cmdline "" \
    "${PACK_ADDR_ARGS[@]}" \
    --output /tmp/u-boot-beyond2lte.img

# Flash to /boot via TWRP dd
echo "[uboot-chainload] Flashing u-boot to ${UFS_BOOT} via TWRP..."
adb push /tmp/u-boot-beyond2lte.img /tmp/u-boot-beyond2lte.img
adb shell "dd if=/tmp/u-boot-beyond2lte.img of=${UFS_BOOT} bs=4096" && echo "[uboot-chainload] Done."
echo ""
echo "[uboot-chainload] U-Boot flashed. Reboot to verify: adb shell twrp reboot"
echo "[uboot-chainload] If the device does not boot, re-flash stock boot.img via Download Mode + heimdall."
echo "[uboot-chainload]   heimdall flash --BOOT <stock-boot.img>"
