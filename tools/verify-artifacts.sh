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
# This is deliberately FAIL-CLOSED:
#   * non-empty files (not just "exists");
#   * boot images must carry a real kernel + ramdisk + dtb (header sizes > 0);
#   * rootfs images must be valid ext4 AND contain the expected payload
#     (device configs + the Nuxel userspace core), so an empty/thin image that
#     merely has an ext4 magic number can never pass;
#   * rootfs images must carry the boot splash: the boot-animation MP4 and the
#     generated Plymouth theme (nuxel.plymouth + frame PNGs). This is the exact
#     content that went missing in CI (no ffmpeg -> theme step silently
#     skipped -> a ~20 MB rootfs instead of the ~60 MB local build);
#   * the s10plus U-Boot image is required only when the mainline set is
#     requested (NUXEL_S10PLUS_UBOOT=1) — matching images/s10plus/build.sh.
#
# Usage:
#   tools/verify-artifacts.sh --device g7power
#   tools/verify-artifacts.sh --device s10plus
#   NUXEL_S10PLUS_UBOOT=1 tools/verify-artifacts.sh --device s10plus
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
        -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
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

# read a little-endian u32 at byte OFFSET
_u32() { od -A n -t u4 -j "$2" -N 4 "$1" 2>/dev/null | tr -d ' \n'; }

# require an Android legacy boot image (v1) that actually carries a kernel,
# a ramdisk and a device tree — an empty/placeholder header must not pass.
_require_boot_image() {
    local f="$1" label="$2"
    [ -s "${f}" ] || { _fail "missing artifact: ${label} (${f})"; return 1; }
    _require_magic "${f}" 0 "41 4e 44 52 4f 49 44 21" "${label} (ANDROID!)" || return 1
    local k ram d
    k="$(_u32 "${f}" 8)"; ram="$(_u32 "${f}" 16)"; d="$(_u32 "${f}" 40)"
    if [ -z "${k}" ] || [ "${k}" -le 0 ] 2>/dev/null; then
        _fail "${label}: boot header kernel_size is empty/zero"; return 1
    fi
    if [ -z "${ram}" ] || [ "${ram}" -le 0 ] 2>/dev/null; then
        _fail "${label}: boot header ramdisk_size is empty/zero"; return 1
    fi
    if [ -z "${d}" ] || [ "${d}" -le 0 ] 2>/dev/null; then
        _fail "${label}: boot header dt_size is empty/zero"; return 1
    fi
    _ok "${label} (boot header kernel=${k}B ramdisk=${ram}B dt=${d}B)"
}

# require a gzip'd arm64 Image (decompresses, ARM64 header magic 0x644d5241)
_require_arm64_image() {
    local f="$1" label="$2"
    [ -s "${f}" ] || { _fail "missing kernel image: ${label} (${f})"; return 1; }
    gzip -t "${f}" 2>/dev/null || { _fail "${label}: not a valid gzip stream"; return 1; }
    local magic
    # Trim both ends: BSD od pads with spaces on both sides, GNU od on the left.
    magic="$(gunzip -c "${f}" 2>/dev/null | od -A n -t x1 -j 56 -N 4 | tr -s ' \n' ' ' | sed -e 's/^ *//' -e 's/ *$//' || true)"
    # ARM64 Image magic = 0x644d5241 -> LE bytes 41 52 4d 64
    if [ "${magic}" != "41 52 4d 64" ]; then
        _fail "${label}: not an ARM64 Linux Image (magic@56='${magic}')"
        return 1
    fi
    _ok "${label} (gzip + arm64 Image)"
}

# require an ext4 image that contains PATH (file or dir). Uses debugfs so we
# verify the *contents*, not just the filesystem magic.
_require_ext4_path() {
    local f="$1" path="$2" label="$3"
    [ -s "${f}" ] || { _fail "missing artifact: ${label} (${f})"; return 1; }
    if ! command -v debugfs >/dev/null 2>&1; then
        _fail "debugfs is required to verify rootfs content (${label}); install e2fsprogs"
        return 1
    fi
    if debugfs -R "stat ${path}" "${f}" 2>/dev/null | grep -q 'Inode:'; then
        _ok "${label}: ${path} present"
    else
        _fail "${label}: expected payload ${path} is missing from the image"
    fi
}

# require an ext4 image whose PATH exists and is at least MIN bytes. Guards
# against a placeholder/missing payload (e.g. an empty boot animation) passing.
_require_ext4_size_ge() {
    local f="$1" path="$2" min="$3" label="$4"
    [ -s "${f}" ] || { _fail "missing artifact: ${label} (${f})"; return 1; }
    if ! command -v debugfs >/dev/null 2>&1; then
        _fail "debugfs is required to verify rootfs content (${label}); install e2fsprogs"
        return 1
    fi
    local sz
    sz="$(debugfs -R "stat ${path}" "${f}" 2>/dev/null \
        | sed -n 's/.*Size: \([0-9][0-9]*\).*/\1/p' | head -1)"
    if [ -z "${sz}" ]; then
        _fail "${label}: expected payload ${path} is missing from the image"
        return 1
    fi
    if [ "${sz}" -lt "${min}" ] 2>/dev/null; then
        _fail "${label}: ${path} is only ${sz} bytes (< ${min}) — payload not populated"
        return 1
    fi
    _ok "${label}: ${path} present (${sz} bytes >= ${min})"
}

KOUT="${NUXEL_ROOT}/kernel/${DEVICE}/.build/out"
OUT="${NUXEL_ROOT}/build/out/${DEVICE}"

echo "== Verifying Nuxel ${DEVICE} artifacts =="

case "${DEVICE}" in
    g7power)
        _require_arm64_image "${KOUT}/arch/arm64/boot/Image.gz" "kernel Image.gz"
        _require_magic "${KOUT}/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb" 0 "d0 0d fe ed" "ocean DTB"
        _require_boot_image "${OUT}/nuxel-ocean-boot.img" "nuxel-ocean-boot.img"
        _require_boot_image "${OUT}/lk2nd.img" "lk2nd.img"
        _require_magic "${OUT}/nuxel-ocean-rootfs.img" 1080 "53 ef" "nuxel-ocean-rootfs.img (ext4)"
        _require_ext4_path "${OUT}/nuxel-ocean-rootfs.img" "/etc/nuxel/device/g7power" "nuxel-ocean-rootfs.img"
        _require_ext4_path "${OUT}/nuxel-ocean-rootfs.img" "/etc/nuxel/nuxel-ocean.conf" "nuxel-ocean-rootfs.img"
        _require_ext4_path "${OUT}/nuxel-ocean-rootfs.img" "/usr/bin/nuxel-bridge" "nuxel-ocean-rootfs.img (userspace)"
        _require_ext4_size_ge "${OUT}/nuxel-ocean-rootfs.img" "/usr/share/nuxel/boot/nuxel-boot-animation.mp4" 1000000 "nuxel-ocean-rootfs.img (boot animation)"
        _require_ext4_path "${OUT}/nuxel-ocean-rootfs.img" "/usr/share/plymouth/themes/nuxel/nuxel.plymouth" "nuxel-ocean-rootfs.img (plymouth theme)"
        _require_ext4_path "${OUT}/nuxel-ocean-rootfs.img" "/usr/share/plymouth/themes/nuxel/frame-0001.png" "nuxel-ocean-rootfs.img (plymouth frames)"
        ;;
    s10plus)
        _require_arm64_image "${KOUT}/arch/arm64/boot/Image.gz" "kernel Image.gz"
        _require_magic "${KOUT}/arch/arm64/boot/dts/samsung/exynos9820-beyond2lte.dtb" 0 "d0 0d fe ed" "beyond2lte DTB"
        _require_boot_image "${OUT}/nuxel-beyond2lte-boot.img" "nuxel-beyond2lte-boot.img"
        _require_magic "${OUT}/nuxel-beyond2lte-rootfs.img" 1080 "53 ef" "nuxel-beyond2lte-rootfs.img (ext4)"
        _require_ext4_path "${OUT}/nuxel-beyond2lte-rootfs.img" "/etc/nuxel/device/s10plus" "nuxel-beyond2lte-rootfs.img"
        _require_ext4_path "${OUT}/nuxel-beyond2lte-rootfs.img" "/etc/nuxel/nuxel-beyond2lte.conf" "nuxel-beyond2lte-rootfs.img"
        _require_ext4_path "${OUT}/nuxel-beyond2lte-rootfs.img" "/usr/bin/nuxel-bridge" "nuxel-beyond2lte-rootfs.img (userspace)"
        _require_ext4_size_ge "${OUT}/nuxel-beyond2lte-rootfs.img" "/usr/share/nuxel/boot/nuxel-boot-animation.mp4" 1000000 "nuxel-beyond2lte-rootfs.img (boot animation)"
        _require_ext4_path "${OUT}/nuxel-beyond2lte-rootfs.img" "/usr/share/plymouth/themes/nuxel/nuxel.plymouth" "nuxel-beyond2lte-rootfs.img (plymouth theme)"
        _require_ext4_path "${OUT}/nuxel-beyond2lte-rootfs.img" "/usr/share/plymouth/themes/nuxel/frame-0001.png" "nuxel-beyond2lte-rootfs.img (plymouth frames)"
        if [ "${NUXEL_S10PLUS_UBOOT:-0}" = "1" ]; then
            _require_boot_image "${OUT}/u-boot-beyond2lte.img" "u-boot-beyond2lte.img (mainline set)"
        fi
        ;;
    *)
        echo "ERROR: unknown device '${DEVICE}'" >&2; exit 2 ;;
esac

if [ "${FAIL}" -ne 0 ]; then
    echo "== ${DEVICE}: ARTIFACT VERIFICATION FAILED =="
    exit 1
fi
echo "== ${DEVICE}: all required artifacts present and valid =="
