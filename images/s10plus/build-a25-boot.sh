#!/usr/bin/env bash
# =============================================================================
# build-a25-boot.sh — build the A25 S10+ BOOT image exactly as it runs on the phone
#
# THE ONE THING THAT MATTERS ON THIS BOARD
#   S-Boot advertises /chosen/linux,initrd-start|end but never populates that
#   memory, so every EXTERNAL ramdisk is discarded by the kernel
#   ("rootfs image is not initramfs (junk in compressed archive)" — measured in
#   A20, docs/s10plus-autonomous-boot-repair/INITRAMFS-DELIVERY-ROOT-CAUSE.md).
#   The only initramfs this device ever executes is the one BUILT INTO THE
#   KERNEL (CONFIG_INITRAMFS_SOURCE). Therefore:
#     * the BOOT container carries a RAW arm64 Image (never Image.gz — S-Boot
#       executes a gzip payload as code: seven silent loads),
#     * that Image embeds the A25 initramfs archive,
#     * the merged board DTB is appended to the container,
#     * the lzma ramdisk copy is carried for non-S-Boot consumers only.
#
# Pipeline:
#   1  tools/s10plus/build-a25-initramfs.sh        -> initramfs.cpio   (repo sources)
#   2  merge board DTB (base + hw_rev overlay)     -> exynos9820-beyond2lte.dtb
#   3  kernel rebuild with CONFIG_INITRAMFS_SOURCE -> Image (raw, arm64)
#   4  boot/s10plus/pack-boot-v1.sh                -> nuxel-beyond2lte-boot.img
#   5  tools/s10plus/verify-a25-boot.py            -> FAIL-CLOSED gate
#
# Required inputs (abort with a clear message when missing):
#   kernel/s10plus/.build/src            (kernel/s10plus/build-kernel.sh --clone)
#   kernel/s10plus/.build/out/.config    (same run)
#   docs/s10plus-device-inventory.md     KERNEL_ADDR / RAMDISK_ADDR / TAGS_ADDR
#   NUXEL_S10PLUS_BOARD_REV              physical board revision (no guessing)
#
# Usage:
#   NUXEL_S10PLUS_BOARD_REV=26 bash images/s10plus/build-a25-boot.sh
#
# Env: NUXEL_S10PLUS_BOARD_REV (required), NUXEL_S10PLUS_OUT (output dir),
#      CROSS_COMPILE, JOBS, NUXEL_S10PLUS_A25_DIR, NUXEL_BOOT_PARTITION_BYTES.
# Exit: 0 ok, 1 build/verification failure, 2 missing input.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export NUXEL_ROOT="${ROOT}"
# Portable SHA-256 (GNU coreutils in CI, BSD/macOS locally).
sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
    else python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"
    fi
}

log() { printf '[a25-boot] %s\n' "$*"; }
err() { printf '[a25-boot][error] %s\n' "$*" >&2; }
die() { err "$*"; exit 1; }

DEVICE="s10plus"
KSRC="${ROOT}/kernel/${DEVICE}/.build/src"
KOUT="${ROOT}/kernel/${DEVICE}/.build/out"
OUT="${NUXEL_S10PLUS_OUT:-${ROOT}/build/out/${DEVICE}}"
CAND="${CAND:-A25}"
A25_DIR="${NUXEL_S10PLUS_A25_DIR:-${ROOT}/build/out/${DEVICE}/debug-candidates/${CAND}}"
CC_PREFIX="${CROSS_COMPILE:-aarch64-linux-gnu-}"
JOBS="${JOBS:-$( (command -v nproc >/dev/null && nproc) || echo 4)}"
PARTITION_BYTES="${NUXEL_BOOT_PARTITION_BYTES:-57671680}"

[ -f "${KSRC}/Makefile" ] || die "kernel tree missing: ${KSRC} (run: NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone)"
[ -f "${KOUT}/.config" ]  || die "kernel .config missing: ${KOUT}/.config (run kernel/s10plus/build-kernel.sh first)"
command -v fdtoverlay >/dev/null 2>&1 || die "fdtoverlay (device-tree-compiler) is required"
command -v python3 >/dev/null 2>&1 || die "python3 required"

# --- 1. initramfs ----------------------------------------------------------
CPIO="${NUXEL_S10PLUS_A25_CPIO:-}"
if [ -n "${CPIO}" ]; then
    [ -s "${CPIO}" ] || die "NUXEL_S10PLUS_A25_CPIO not found: ${CPIO}"
    log "using supplied initramfs: ${CPIO}"
else
    log "building the A25 initramfs from repo sources"
    CAND="${CAND}" NUXEL_S10PLUS_A25_DIR="${A25_DIR}" \
        bash "${ROOT}/tools/s10plus/build-a25-initramfs.sh"
    CPIO="${A25_DIR}/initramfs.cpio"
fi
[ -s "${CPIO}" ] || die "no initramfs archive produced"
CPIO_SHA="$(sha256 "${CPIO}")"
log "initramfs: $(wc -c <"${CPIO}" | tr -d ' ') bytes sha256 ${CPIO_SHA}"
mkdir -p "${OUT}"

# --- 2. board DTB (SoC base + exact hw_rev overlay) ------------------------
BOARD_REV="${NUXEL_S10PLUS_BOARD_REV:-}"
[[ "${BOARD_REV}" =~ ^[0-9]+$ ]] || die "NUXEL_S10PLUS_BOARD_REV must be the physical board revision (digits); refusing to guess"
DTB_BASE="${KOUT}/arch/arm64/boot/dts/exynos/exynos9820.dtb"
DTB_SAMSUNG="${KOUT}/arch/arm64/boot/dts/samsung"
DTB_MERGED="${DTB_SAMSUNG}/exynos9820-beyond2lte.dtb"
[ -s "${DTB_BASE}" ] || die "missing base DTB: ${DTB_BASE}"
_overlay="${DTB_SAMSUNG}/exynos9820-beyond2lte_eur_open_${BOARD_REV}.dtbo"
[ -s "${_overlay}" ] || die "missing exact board overlay: ${_overlay}"
log "merging board revision ${BOARD_REV}: $(basename "${_overlay}")"
fdtoverlay -i "${DTB_BASE}" -o "${DTB_MERGED}" "${_overlay}" || die "device-tree merge failed"
[ -s "${DTB_MERGED}" ] || die "merged DTB not produced"

# --- 3. kernel with the initramfs EMBEDDED --------------------------------
# Same relaxation as kernel/s10plus/build-kernel.sh: the 4.14 downstream tree
# hard-codes -Werror in places KCFLAGS cannot reach, so strip it (idempotent).
bash "${ROOT}/tools/kernel-relax-werror.sh" "${KSRC}" >/dev/null 2>&1 || true

KCFLAGS=""
_cc="${CC_PREFIX}gcc"
for _f in -fcommon -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration \
          -Wno-error=int-conversion -Wno-error=implicit-int -Wno-error=strict-prototypes \
          -Wno-error=date-time -Wno-error=designated-init -Wno-error=return-mismatch \
          -Wno-error=discarded-qualifiers -Wno-error=pointer-sign -Wno-error; do
    if echo | "${_cc}" "${_f}" -c -x c - -o /dev/null >/dev/null 2>&1; then
        KCFLAGS="${KCFLAGS:+${KCFLAGS} }${_f}"
    fi
done

log "configuring CONFIG_INITRAMFS_SOURCE=${CPIO}"
if grep -q '^CONFIG_INITRAMFS_SOURCE=' "${KOUT}/.config"; then
    cp -f "${KOUT}/.config" "${KOUT}/.config.nuxel-a25.bak"
    sed -i.tmp "s|^CONFIG_INITRAMFS_SOURCE=.*|CONFIG_INITRAMFS_SOURCE=\"${CPIO}\"|" "${KOUT}/.config"
    rm -f "${KOUT}/.config.tmp"
else
    printf 'CONFIG_INITRAMFS_SOURCE="%s"\n' "${CPIO}" >> "${KOUT}/.config"
fi
grep -q "^CONFIG_INITRAMFS_SOURCE=\"${CPIO}\"" "${KOUT}/.config" \
    || die "CONFIG_INITRAMFS_SOURCE was not applied to ${KOUT}/.config"
grep -E '^CONFIG_INITRAMFS_(SOURCE|COMPRESSION)' "${KOUT}/.config" || true

log "building raw arm64 Image (jobs=${JOBS}) — initramfs embedded, no external ramdisk dependency"
make -C "${KSRC}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CC_PREFIX}" \
     KCFLAGS="${KCFLAGS}" olddefconfig >/dev/null
make -C "${KSRC}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CC_PREFIX}" \
     KCFLAGS="${KCFLAGS}" -j"${JOBS}" Image
IMAGE="${KOUT}/arch/arm64/boot/Image"
[ -s "${IMAGE}" ] || die "kernel Image not produced: ${IMAGE}"
cp -f "${IMAGE}" "${OUT}/Image-A25"
log "Image: $(wc -c <"${OUT}/Image-A25" | tr -d ' ') bytes"

# --- 4. BOOT container ----------------------------------------------------
# lzma-alone ramdisk (dict 8 MiB, end-of-stream marker), 64 KiB zero padding
# inside the stream, compressed blob aligned to 64 KiB — same container the
# hardware ran with, so nothing about the delivery changes vs the proven build.
RAMDISK="${OUT}/initramfs-A25.ramdisk.lzma"
python3 - "$CPIO" "$RAMDISK" <<'PY'
import lzma, sys
cpio, out = sys.argv[1], sys.argv[2]
data = open(cpio, "rb").read() + b"\x00" * 65536
filt = [{"id": lzma.FILTER_LZMA1, "preset": 6, "dict_size": 1 << 23}]
blob = lzma.compress(data, format=lzma.FORMAT_ALONE, filters=filt)
pad = (-len(blob)) % 65536
open(out, "wb").write(blob + b"\x00" * pad)
print("ramdisk lzma: %d bytes (payload %d, pad %d)" % (len(blob) + pad, len(blob), pad))
PY

INVENTORY="${ROOT}/docs/s10plus-device-inventory.md"
[ -f "${INVENTORY}" ] || die "missing ${INVENTORY}"
addr() { awk -v k="$1" '$0 ~ "^"k":" {print $2; exit}' "${INVENTORY}"; }
K_ADDR="$(addr KERNEL_ADDR)"; R_ADDR="$(addr RAMDISK_ADDR)"; T_ADDR="$(addr TAGS_ADDR)"
for pair in "KERNEL_ADDR:${K_ADDR}" "RAMDISK_ADDR:${R_ADDR}" "TAGS_ADDR:${T_ADDR}"; do
    [[ "${pair#*:}" =~ ^0x[0-9a-fA-F]+$ ]] || die "${pair%%:*} ('${pair#*:}') is not a hex address in ${INVENTORY}"
done

CMDLINE="buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw"
BOOTIMG="${OUT}/nuxel-beyond2lte-boot.img"
log "packing ${BOOTIMG} (legacy v1 header, page 2048)"
# --v1-spec is REQUIRED: it writes a spec-compliant boot_img_hdr_v1
# (header_version=1 at offset 40). Without it the packer uses the legacy layout
# that stored the DTB size at offset 40, which S-Boot logs as
# "[UFDT] BOOT IMG HDR V376101" — the exact defect the proven A25 image does not
# have, and which tools/s10plus/verify-a25-boot.py rejects.
python3 "${ROOT}/boot/s10plus/pack-boot-v1.sh" \
    --kernel  "${OUT}/Image-A25" \
    --ramdisk "${RAMDISK}" \
    --dtb     "${DTB_MERGED}" \
    --cmdline "${CMDLINE}" \
    --kernel-addr "${K_ADDR}" --ramdisk-addr "${R_ADDR}" --tags-addr "${T_ADDR}" \
    --v1-spec \
    --output  "${BOOTIMG}"

# Keep the archive next to the boot image: the verifier (and verify-artifacts.sh)
# proves the Image embeds *this* file, not some other candidate's archive.
cp -f "${CPIO}" "${OUT}/initramfs-A25.cpio"

# --- 5. fail-closed verification ------------------------------------------
python3 "${ROOT}/tools/s10plus/verify-a25-boot.py" \
    --boot-image "${BOOTIMG}" \
    --kernel "${OUT}/Image-A25" \
    --initramfs "${CPIO}" \
    --partition-bytes "${PARTITION_BYTES}" \
    --report "${OUT}/a25-boot.report.txt"

BOOT_SHA="$(sha256 "${BOOTIMG}")"
cat > "${OUT}/a25-boot.manifest.json" <<JSON
{
  "candidate": "${CAND}",
  "device": "s10plus",
  "board_rev": "${BOARD_REV}",
  "initramfs_sha256": "${CPIO_SHA}",
  "initramfs_bytes": $(wc -c <"${CPIO}" | tr -d ' '),
  "kernel_image": "Image-A25",
  "kernel_sha256": "$(sha256 "${OUT}/Image-A25")",
  "kernel_bytes": $(wc -c <"${OUT}/Image-A25" | tr -d ' '),
  "boot_image_sha256": "${BOOT_SHA}",
  "boot_image_bytes": $(wc -c <"${BOOTIMG}" | tr -d ' '),
  "partition_bytes": ${PARTITION_BYTES}
}
JSON
log "boot.img: $(wc -c <"${BOOTIMG}" | tr -d ' ') bytes sha256 ${BOOT_SHA}"
log "A25_BOOT_BUILD_OK  ${BOOTIMG}"
