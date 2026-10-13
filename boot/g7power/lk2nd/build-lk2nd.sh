#!/usr/bin/env bash
# =============================================================================
# Nuxel G7 Power — build the lk2nd second-stage bootloader (msm8953 / ocean)
#
# lk2nd (msm8916-mainline/lk2nd) replaces the stock ABOOT fastboot with one that
# understands mainline DTBs + cmdline, and is REQUIRED on the G7 Power boot
# chain:  PBL -> stock ABOOT -> lk2nd -> mainline Linux -> Nuxel initramfs.
# Without lk2nd.img the Nuxel boot image cannot be flashed on the device, so the
# G7 Power artifact set is INCOMPLETE until this script has run.
#
# Usage:
#   bash boot/g7power/lk2nd/build-lk2nd.sh [--clean] [--jobs N]
#        [--repo URL] [--ref REF] [--toolchain PREFIX]
#
# Output:
#   boot/g7power/lk2nd/.build/build-msm8953/lk2nd.img
#     (the path images/g7power/build.sh copies into build/out/g7power/lk2nd.img)
#
# Requirements: git, make, and an arm-none-eabi cross toolchain
# (`gcc-arm-none-eabi` on Debian/Ubuntu). This script never flashes anything.
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
L2K_DIR="${NUXEL_ROOT}/boot/g7power/lk2nd"
SRC="${L2K_DIR}/.build/src"
OUT="${L2K_DIR}/.build/build-msm8953"

REPO="${LK2ND_REPO:-https://github.com/msm8916-mainline/lk2nd}"
REF="${LK2ND_REF:-}"
TOOLCHAIN="${TOOLCHAIN_PREFIX:-arm-none-eabi-}"
JOBS="${JOBS:-$( (command -v nproc >/dev/null && nproc) || echo 4)}"
DO_CLEAN=0

usage() { grep '^#' "$0" | sed 's/^# \{0,1\}//' | sed -n '1,30p'; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --clean)   DO_CLEAN=1; shift ;;
        --jobs)    JOBS="$2"; shift 2 ;;
        --repo)    REPO="$2"; shift 2 ;;
        --ref)     REF="$2"; shift 2 ;;
        --toolchain) TOOLCHAIN="$2"; shift 2 ;;
        *) echo "Unknown: $1" >&2; exit 1 ;;
    esac
done

log() { echo "[nuxel-g7power-lk2nd] $*"; }

CC_BIN="${TOOLCHAIN}gcc"
command -v "${CC_BIN}" >/dev/null 2>&1 || {
    echo "[nuxel-g7power-lk2nd] ERROR: ${CC_BIN} not found." >&2
    echo "[nuxel-g7power-lk2nd]        Install gcc-arm-none-eabi (Debian/Ubuntu) or pass --toolchain." >&2
    exit 1
}

mkdir -p "${L2K_DIR}/.build"

if [ "${DO_CLEAN}" -eq 1 ]; then
    log "Cleaning ${SRC} and ${OUT}"
    rm -rf "${SRC}" "${OUT}"
fi

if [ ! -d "${SRC}/.git" ]; then
    log "Cloning ${REPO} -> ${SRC}"
    rm -rf "${SRC}"
    if [ -n "${REF}" ]; then
        git clone --depth=1 --branch "${REF}" "${REPO}" "${SRC}"
    else
        git clone --depth=1 "${REPO}" "${SRC}"
    fi
else
    log "Reusing existing lk2nd checkout at ${SRC}"
fi

log "Building lk2nd msm8953 (toolchain=${TOOLCHAIN}, jobs=${JOBS})..."
make -C "${SRC}" -j"${JOBS}" TOOLCHAIN_PREFIX="${TOOLCHAIN}" lk2nd-msm8953

# The lk2nd build writes build-lk2nd-msm8953/lk2nd.img inside its own tree.
BUILT_IMG="${SRC}/build-lk2nd-msm8953/lk2nd.img"
[ -s "${BUILT_IMG}" ] || {
    echo "[nuxel-g7power-lk2nd] ERROR: ${BUILT_IMG} not produced by the build." >&2
    exit 1
}

mkdir -p "${OUT}"
cp -f "${BUILT_IMG}" "${OUT}/lk2nd.img"
log "lk2nd.img: $(ls -lh "${OUT}/lk2nd.img" | awk '{print $5}') -> ${OUT}/lk2nd.img"
log "Done."
