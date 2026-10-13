#!/usr/bin/env bash
# =============================================================================
# Nuxel S10+ Kernel Build Wrapper — Samsung Galaxy S10+ (beyond2lte)
#
# AUTHORITATIVE kernel source (verified 2026-10-11):
#   https://github.com/Linux4/android_kernel_samsung_exynos9820
#   commit f7194c1d15eded1c2a1a4dc63825b26103435cc0  (Linux 4.14.253 downstream)
#   defconfig: exynos9820-beyond2lte_defconfig
#
# This is the *downstream* Samsung Exynos 9820 kernel fork that the
# postmarketOS S10 port (device-samsung-beyond1lte) actually builds and boots.
# It is the kernel that matches the vendor firmware in firmware/s10plus/
# (bcmdhd WiFi, CS47L93/CS35L40 audio, S3NRN82 NFC, FIMC-IS camera).
#
# CORRECTION (2026-10-11): the previous version of this script cloned
#   https://github.com/postmarketOS/linux-postmarketos branch exynos9820
# which DOES NOT EXIST (404). There is no `linux-postmarketos-exynos9820`
# package in pmaports either — the S10 uses `linux-samsung-beyond1lte`
# (this downstream tree). The `linux-postmarketos-exynos9820` / "close-to-
# mainline" claim in the older bring-up docs was aspirational, not real.
#
# Usage:
#   NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh [--clone] [--clean]
#       [--jobs N] [--cross <prefix>] [--help]
#
# Outputs (under kernel/s10plus/.build/out/):
#   arch/arm64/boot/Image.gz
#   arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_*.dtb
#
# Flashing is heimdall (BOOT+SYSTEM) or TWRP adb+dd — there is NO fastboot.
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEVICE_KEY="s10plus"

DOWNSTREAM_REPO="https://github.com/Linux4/android_kernel_samsung_exynos9820"
DOWNSTREAM_COMMIT="f7194c1d15eded1c2a1a4dc63825b26103435cc0"
DEFCONFIG="exynos9820-beyond2lte_defconfig"

# The downstream Samsung Makefile hardcodes its internal Android toolchain as
# the default CROSS_COMPILE:
#   CROSS_COMPILE ?= $(srctree)/toolchain/gcc-cfp/.../aarch64-linux-android-
# That toolchain is not shipped with the source, so a bare `make` dies with
#   .../aarch64-linux-android-gcc: No such file or directory
#   Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: ... not supported by compiler
# We therefore always pass CROSS_COMPILE explicitly on the make command line
# (command-line assignments override the Makefile's `?=` default). The default
# matches the Debian/Ubuntu `gcc-aarch64-linux-gnu` package used in CI; override
# with --cross / $CROSS_COMPILE for another toolchain (or `--cross ''` for a
# native aarch64 host build).
CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"

# GCC 14/15 changed several diagnostics to hard errors by default; the 4.14
# downstream tree predates that. Relax them (this is exactly the class of fix
# the postmarketOS downstream-kernel tooling applies).
DEFAULT_KCFLAGS="-fcommon -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration -Wno-error=int-conversion -Wno-error=implicit-int -Wno-error=return-mismatch -Wno-error=discarded-qualifiers -Wno-error=pointer-sign"

DO_CLONE=0
DO_CLEAN=0
JOBS="${JOBS:-$( (command -v nproc >/dev/null && nproc) || echo 4)}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) grep '^#' "$0" | sed -n '2,40p' | sed 's/^# \{0,1\}//'; exit 0 ;;
        --clone) DO_CLONE=1; shift ;;
        --clean) DO_CLEAN=1; shift ;;
        --jobs)  JOBS="$2"; shift 2 ;;
        --cross) CROSS_COMPILE="$2"; shift 2 ;;
        --device) export NUXEL_DEVICE="$2"; shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || {
    echo "ERROR: kernel/s10plus/build-kernel.sh is ONLY for s10plus. Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

KSRC="${NUXEL_ROOT}/kernel/s10plus/.build/src"
KOUT="${NUXEL_ROOT}/kernel/s10plus/.build/out"

echo "[nuxel-s10plus-kernel] Device: ${DEVICE_KEY} (beyond2lte, Exynos 9820)"
echo "[nuxel-s10plus-kernel] Kernel: ${DOWNSTREAM_REPO##*/}@${DOWNSTREAM_COMMIT:0:12} (Linux 4.14.253 downstream)"
echo "[nuxel-s10plus-kernel] Cross:   ${CROSS_COMPILE:-<native, empty>}"
echo "[nuxel-s10plus-kernel] Defconfig: ${DEFCONFIG}"
echo "[nuxel-s10plus-kernel] Output:  ${KOUT}"

[[ $DO_CLEAN -eq 1 ]] && { echo "[kernel] Cleaning ${KOUT}"; rm -rf "${KOUT}"; }
mkdir -p "${KOUT}"

# --- clone / fetch ---
if [[ $DO_CLONE -eq 1 || ! -d "${KSRC}/.git" ]]; then
    if [ -d "${KSRC}" ] && [ ! -e "${KSRC}/.git" ] && [ -f "${KSRC}/Makefile" ]; then
        echo "[kernel] Using existing extracted tree at ${KSRC}"
    else
        echo "[kernel] Cloning ${DOWNSTREAM_REPO} (commit ${DOWNSTREAM_COMMIT:0:12})..."
        git clone --filter=blob:none --no-checkout "${DOWNSTREAM_REPO}" "${KSRC}"
        git -C "${KSRC}" checkout "${DOWNSTREAM_COMMIT}"
    fi
fi

# --- configure ---
cd "${KSRC}"
make O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    KCFLAGS="${DEFAULT_KCFLAGS}" "${DEFCONFIG}"

# --- build ---
echo "[kernel] Building Image.gz + dtbs (jobs=${JOBS})..."
make O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    -j"${JOBS}" KCFLAGS="${DEFAULT_KCFLAGS}" Image.gz dtbs

echo "[kernel] Done."
ls -lh "${KOUT}/arch/arm64/boot/Image.gz" 2>/dev/null || echo "[kernel] WARN: Image.gz missing"
find "${KOUT}/arch/arm64/boot/dts" -name 'exynos9820-beyond2lte*.dtb' 2>/dev/null || true
