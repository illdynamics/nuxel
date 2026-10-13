#!/usr/bin/env bash
# =============================================================================
# Nuxel G7 Power Kernel Build Wrapper — linux-postmarketos-qcom-msm8953
# Device: Motorola Moto G7 Power (XT1955), codename ocean
# Kernel: msm8953-mainline/linux (close-to-mainline Snapdragon 632 / SDM632)
# =============================================================================
# Usage:
#   NUXEL_DEVICE=g7power kernel/g7power/build-kernel.sh [--clone] [--clean]
#       [--jobs N] [--cross <prefix>] [--device g7power] [--help]
# G7 Power is A-only (no A/B slots) with a legacy boot image header v1
# (page 2048). Flashing is two-phase fastboot (stock ABOOT: dtbo -> lk2nd,
# then lk2nd fastboot: boot -> userdata) — see boot/g7power/flash.sh.
# This wrapper only builds; it never flashes anything.
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEVICE_KEY="g7power"
KOUT="${NUXEL_ROOT}/kernel/g7power/.build/out"
KSRC="${NUXEL_ROOT}/kernel/g7power/.build/src"
PATCHES="${NUXEL_ROOT}/kernel/g7power/patches"
DEFCONFIG="${NUXEL_ROOT}/kernel/g7power/defconfig"

CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
JOBS="${JOBS:-$(nproc)}"

MSM8953_KERNEL_REPO="https://github.com/msm8953-mainline/linux"
MSM8953_KERNEL_BRANCH="master"

echo "[nuxel-g7power-kernel] Device:    ${DEVICE_KEY} (ocean, SDM632/msm8953)"
echo "[nuxel-g7power-kernel] Kernel:    linux-postmarketos-qcom-msm8953 (msm8953-mainline/linux)"
echo "[nuxel-g7power-kernel] Cross:     ${CROSS_COMPILE}"
echo "[nuxel-g7power-kernel] Output:    ${KOUT}"

DO_CLONE=0; DO_BUILD=1; DO_CLEAN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)  grep '^#' "$0" | head -12; exit 0 ;;
        --clone)    DO_CLONE=1; shift ;;
        --clean)    DO_CLEAN=1; shift ;;
        --jobs)     JOBS="$2"; shift 2 ;;
        --cross)    CROSS_COMPILE="$2"; shift 2 ;;
        --device)   export NUXEL_DEVICE="$2"; shift 2 ;;  # forwarded to the device selector
        *)          echo "Unknown: $1"; exit 1 ;;
    esac
done

# Device guard — G7 Power only. Explicit selection required (env or --device).
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh"
[ "${NUXEL_DEVICE_KEY}" = "g7power" ] || {
    echo "ERROR: kernel/g7power/build-kernel.sh is ONLY for g7power. Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

# The selector guarantees NUXEL_DEVICE_DIR=g7power here. Re-derive every
# per-device path from it so this script can never address another device's
# kernel tree even if a future refactor changes the directory naming.
KOUT="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/out"
KSRC="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/src"
PATCHES="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/patches"
DEFCONFIG="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/defconfig"

# ---------------------------------------------------------------------------
# Inventory gate (Phase 0) — see docs/g7power-device-inventory.md
# Blocks real build operations until the operator has filled the critical
# fields from the physical device. Never blocks --help (handled above).
# ---------------------------------------------------------------------------
_check_g7power_inventory() { local inv="${NUXEL_ROOT}/docs/g7power-device-inventory.md"; [ -f "${inv}" ] || { echo "ERROR: docs/g7power-device-inventory.md missing — run Phase 0 inventory first."; exit 1; }; if grep -qE "KERNEL_ADDR:.*PLACEHOLDER|RAMDISK_ADDR:.*PLACEHOLDER|TAGS_ADDR:.*PLACEHOLDER|WIFI_FW_FILENAMES:.*UNKNOWN" "${inv}"; then echo "ERROR: G7 Power device inventory incomplete."; echo "       Run Phase 0 commands in docs/g7power-device-inventory.md"; echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, WIFI_FW_FILENAMES"; exit 1; fi; }
_check_g7power_inventory

mkdir -p "${KOUT}" "${KSRC}"

if [[ $DO_CLONE -eq 1 ]] || [[ ! -d "${KSRC}/.git" ]]; then
    echo "[kernel] Cloning msm8953-mainline/linux..."
    git clone --depth=1 -b "${MSM8953_KERNEL_BRANCH}" \
        "${MSM8953_KERNEL_REPO}" "${KSRC}" || {
        echo "[kernel] ERROR: Clone failed. Check network access."
        echo "[kernel] Repo: ${MSM8953_KERNEL_REPO}"
        exit 1
    }
fi

if [[ $DO_CLEAN -eq 1 ]]; then
    make -C "${KSRC}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" mrproper
fi

echo "[kernel] Applying Nuxel patches..."
for patch in "${PATCHES}"/*.patch; do
    [[ -f "$patch" ]] || continue
    echo "[kernel] Applying: $(basename "$patch")"
    git -C "${KSRC}" apply "$patch" 2>/dev/null || {
        echo "[kernel] WARN: Patch $(basename "$patch") did not apply cleanly."
        echo "[kernel] See ${PATCHES}/$(basename "$patch" .patch).README"
    }
done

echo "[kernel] Configuring (msm8953_defconfig + Nuxel fragment)..."
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" msm8953_defconfig 2>/dev/null || \
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" defconfig
"${KSRC}/scripts/kconfig/merge_config.sh" -m \
    "${KOUT}/.config" "${DEFCONFIG}"
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" olddefconfig

if [[ $DO_BUILD -eq 1 ]]; then
    echo "[kernel] Building Image.gz + DTBs (jobs=${JOBS})..."
    make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
        O="${KOUT}" -j"${JOBS}" Image.gz dtbs modules
fi

# Install modules into a staging dir
MODULES_STAGING="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/modules-staging"
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" INSTALL_MOD_PATH="${MODULES_STAGING}" modules_install

echo ""
echo "[kernel] Done."
echo "[kernel] Image.gz:  ${KOUT}/arch/arm64/boot/Image.gz"
echo "[kernel] DTBs:      ${KOUT}/arch/arm64/boot/dts/qcom/"
echo "[kernel] DTB:       ${KOUT}/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb"
echo "[kernel] Modules:   ${MODULES_STAGING}/lib/modules/"
ls -lh "${KOUT}/arch/arm64/boot/Image.gz" 2>/dev/null || \
    echo "[kernel] WARN: Image.gz not found — build may have failed."
if ! compgen -G "${KOUT}/arch/arm64/boot/dts/qcom/*ocean*" > /dev/null; then
    echo "[kernel] WARN: ocean DTB not found — check DTS availability in tree."
fi
