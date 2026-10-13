#!/usr/bin/env bash
# =============================================================================
# Nuxel — strict artifact verifier (CI gate)
#
# Asserts that a device's build actually produced real, non-fabricated,
# structurally-valid artifacts. The release workflow runs this AFTER the image
# build and BEFORE packaging, so a job can never go green (and a release can
# never be published) when the kernel / initramfs / boot image / rootfs are
# missing or are not what they claim to be.
#
# Usage:
#   tools/verify-artifacts.sh --device g7power
#   tools/verify-artifacts.sh --device s10plus
#
# Exit code: 0 = every required artifact present + valid; 1 = at least one
#            check failed (details printed with ::error:: for GitHub Actions).
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEVICE=""
FAIL=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --device) DEVICE="$2"; shift 2 ;;
        -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "Unknown: $1" >&2; exit 2 ;;
    esac
done
[ -n "${DEVICE}" ] || { echo "ERROR: --device is required" >&2; exit 2; }

_fail() { echo "::error::$*"; FAIL=1; }
_ok()   { echo "  [ok]   $*"; }

# require a non-empty regular file
_require() {
    local f="$1" label="${2:-$1}"
    if [ ! -s "${f}" ]; then
        _fail "missing/empty artifact: ${label} (${f})"
        return 1
    fi
    _ok "${label} ($(du -h "${f}" | awk '{print $1}'))"
}

# require a file whose first bytes at OFFSET match HEXBYTES (space separated)
_require_magic() {
    local f="$1" offset="$2" want="$3" label="$4"
    [ -s "${f}" ] || { _fail "missing artifact: ${label} (${f})"; return 1; }
    local got nwant
    nwant="$(printf '%s\n' ${want} | wc -l | tr -d ' ')"
    got="$(od -A n -t x1 -j "${offset}" -N "${nwant}" "${f}" 2>/dev/null | tr -s ' \n' ' ' | sed -e 's/^ *//' -e 's/ *$//')"
    if [ "${got}" != "${want}" ]; then
        _fail "${label}: magic mismatch (want '${want}' at ${offset}, got '${got}')"
        return 1
    fi
    _ok "${label} (magic ok)"
}

# require a gzip'd arm64 Image (decompresses, ARM64 header magic 0x644d5241)
_require_arm64_image() {
    local f="$1" label="$2"
    [ -s "${f}" ] || { _fail "missing kernel image: ${label} (${f})"; return 1; }
    gzip -t "${f}" 2>/dev/null || { _fail "${label}: not a valid gzip stream"; return 1; }
    local magic
    magic="$(gunzip -c "${f}" 2>/dev/null | od -A n -t x1 -j 56 -N 4 | tr -s ' ' | sed 's/^ //' || true)"
    # ARM64 Image magic = 0x644d5241 -> LE bytes 41 52 4d 64
    if [ "${magic}" != "41 52 4d 64" ]; then
        _fail "${label}: not an ARM64 Linux Image (magic@56='${magic}')"
        return 1
    fi
    _ok "${label} (gzip + arm64 Image)"
}

KOUT="${NUXEL_ROOT}/kernel/${DEVICE}/.build/out"
OUT="${NUXEL_ROOT}/build/out/${DEVICE}"

echo "== Verifying Nuxel ${DEVICE} artifacts =="

case "${DEVICE}" in
    g7power)
        _require_arm64_image "${KOUT}/arch/arm64/boot/Image.gz" "kernel Image.gz"
        _require_magic "${KOUT}/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb" 0 "d0 0d fe ed" "ocean DTB"
        _require_magic "${OUT}/nuxel-ocean-boot.img" 0 "41 4e 44 52 4f 49 44 21" "nuxel-ocean-boot.img (ANDROID!)"
        _require_magic "${OUT}/nuxel-ocean-rootfs.img" 1080 "53 ef" "nuxel-ocean-rootfs.img (ext4)"
        _require_magic "${OUT}/lk2nd.img" 0 "41 4e 44 52 4f 49 44 21" "lk2nd.img (ANDROID!)"
        ;;
    s10plus)
        _require_arm64_image "${KOUT}/arch/arm64/boot/Image.gz" "kernel Image.gz"
        _require_magic "${KOUT}/arch/arm64/boot/dts/samsung/exynos9820-beyond2lte.dtb" 0 "d0 0d fe ed" "beyond2lte DTB"
        _require_magic "${OUT}/nuxel-beyond2lte-boot.img" 0 "41 4e 44 52 4f 49 44 21" "nuxel-beyond2lte-boot.img (ANDROID!)"
        _require_magic "${OUT}/nuxel-beyond2lte-rootfs.img" 1080 "53 ef" "nuxel-beyond2lte-rootfs.img (ext4)"
        ;;
    *)
        echo "ERROR: unknown device '${DEVICE}'" >&2; exit 2 ;;
esac

if [ "${FAIL}" -ne 0 ]; then
    echo "== ${DEVICE}: ARTIFACT VERIFICATION FAILED =="
    exit 1
fi
echo "== ${DEVICE}: all required artifacts present and valid =="
