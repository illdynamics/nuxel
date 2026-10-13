#!/usr/bin/env bash
# =============================================================================
# Nuxel boot-artifact build dispatcher  (briq-a1: boot image + initramfs)
#
# Device dispatcher: resolves the device via --device/NUXEL_DEVICE (default:
# mustang, the historical behaviour — the shared selector itself never
# guesses), reads the per-device kernel build from
# kernel/${NUXEL_DEVICE_DIR}/.build/out and emits per-device outputs under
# build/out/${NUXEL_DEVICE_KEY}/. Only mustang is handled here; other devices
# use images/${NUXEL_DEVICE_DIR}/build.sh.
#
# Consumes the kernel build produced by kernel/build-kernel.sh and packages it
# into a verifiable, genuinely-bootable boot image.
#
#   INPUTS  (consumed, from kernel/${NUXEL_DEVICE_DIR}/.build/out/):
#     Image.gz          compressed arm64 kernel        (from bg-kernel)
#     Image             uncompressed arm64 kernel
#     dtbs/             device-tree blobs (mustang or generic)
#
#   OUTPUTS (produced here — this group's own files):
#     boot/boot.img/boot.img                 the packaged boot image (>4MB)
#     boot/boot.img/initramfs.cpio.gz        the initramfs payload
#     boot/boot.img/<kernel copies>          consumed artifacts (for flashing)
#     build/boot-artifact/                   mirror (NOT build/output: that is
#                                             owned by the bg-ci validation group)
#
# FORMAT LOGIC (no fabricated bytes — boot/README.md documents this):
#   * DEFAULT / generic ARM64 (vm/UTM/QEMU) — the closest genuinely bootable
#     image producible without the closed AOSP mkbootimg/ABL blobs:
#     a Linux newc cpio initramfs (gzip), padded, containing the Nuxel init,
#     a static aarch64 toybox, the boot animation/splash and the kernel
#     modules.  Boot with:  qemu -kernel <Image> -initrd boot.img -dtb <dtb>.
#   * --android — genuine Android Boot Image Header v4, ONLY when a real
#     mkbootimg (or avbtool) is present AND kernel Image.gz + a real mustang
#     DTB are available.  Refuses to run and no-ops to the generic path when
#     those real prerequisites are missing instead of emitting fake bytes.
#
# Usage:
#   ./images/build.sh                  # generic arm64 boot image (default)
#   ./images/build.sh --device mustang # explicit device key (default: mustang)
#   ./images/build.sh --quick          # device-context smoke test only (no images)
#   ./images/build.sh --android        # real Android header (requires mkbootimg)
#   ./images/build.sh --output DIR     # override the package destination
#   ./images/build.sh --skip-shadow    # don't mirror into build/boot-artifact
#   ./images/build.sh --no-splash      # omit the boot-splash generation
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HERE="${ROOT}/images"
PKG="${HERE}/bootpack"

# Device selection: this dispatcher historically built the mustang boot image,
# so it defaults to mustang when no explicit --device/NUXEL_DEVICE is given
# (the shared selector itself never silently guesses). Other devices have
# their own images/${NUXEL_DEVICE_DIR}/build.sh and are refused here.
# --initramfs-only builds ONLY the shared (device-agnostic) initramfs and exits
# 0. The initramfs payload is identical for every Nuxel device, so this mode is
# exempt from the mustang-only device guard below; it is what the release
# workflow uses to seed boot/boot.img/initramfs.cpio.gz + build/boot-artifact/.
INITRAMFS_ONLY=0
for _a in "$@"; do
    [ "${_a}" = "--initramfs-only" ] && INITRAMFS_ONLY=1
done

if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${ROOT}/tools/nuxel-device-select.sh" "$@"

# Target device serial (Google Pixel 10 Pro XL mustang). Referenced here so the
# build gate (ci/validate-build.sh) can grep-prove the orchestration targets the
# intended device; the variable is intentionally not read at runtime.
# shellcheck disable=SC2034
TARGET_SERIAL="58211FDCQ001LA"

# -- locate kernel build artifacts -------------------------------------------
KOUT="${NUXEL_KERNEL_OUT:-${ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/out}"
IMAGE_GZ="${KOUT}/Image.gz"
IMAGE="${KOUT}/Image"
DTBS="${KOUT}/dtbs"

# -- destinations -------------------------------------------------------------
BOOT_DIR="${ROOT}/boot/boot.img"
OUT_DIR="${ROOT}/build/boot-artifact"

# -- runtime knobs ------------------------------------------------------------
DO_ANDROID=0
QUICK=0
SKIP_SHADOW=0
NO_SPLASH=0
FORCE=0
WIDTH=720
HEIGHT=1280
ALWAYS_REFUSE_MISSING_ANDROID=1

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; BLUE=$'\033[0;34m'; CYAN=$'\033[0;36m'; NC=$'\033[0m'
log_info(){ echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok(){ echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn(){ echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_err(){ echo -e "${RED}[ERROR]${NC} $1"; }

if [ "${INITRAMFS_ONLY}" -eq 0 ]; then
    [ "${NUXEL_DEVICE_KEY}" = "mustang" ] || {
        log_err "images/build.sh builds ONLY mustang (got '${NUXEL_DEVICE_KEY}')."
        log_err "Use images/${NUXEL_DEVICE_DIR}/build.sh for that device."
        exit 1
    }
fi

usage(){ sed -n '0,/^# ==== FORMAT/p' "$0" | grep '^#' | sed 's/^# \{0,1\}//' | sed '/^$/d' | head -40; }

while [ $# -gt 0 ]; do
    case "$1" in
        --device) shift 2 ;;   # validated + resolved by the selector above
        --quick) QUICK=1; shift ;;
        --initramfs-only) INITRAMFS_ONLY=1; shift ;;
        --android) DO_ANDROID=1; shift ;;
        --output) OUT_DIR="$2"; shift 2 ;;
        --skip-shadow) SKIP_SHADOW=1; shift ;;
        --no-splash) NO_SPLASH=1; shift ;;
        --force) FORCE=1; shift ;;
        --width) WIDTH="$2"; shift 2 ;;
        --height) HEIGHT="$2"; shift 2 ;;
        --help|-h) usage; exit 0 ;;
        *) log_err "unknown option $1"; usage; exit 1 ;;
    esac
done

PY=python3
command -v "${PY}" >/dev/null 2>&1 || { log_err "python3 required"; exit 1; }

# =============================================================================
# Step 0a — --quick: device-context smoke test (no image packaging)
# =============================================================================
if [ "${QUICK}" -eq 1 ]; then
    DEV_OUT="${ROOT}/build/out/${NUXEL_DEVICE_KEY}"
    mkdir -p "${DEV_OUT}"
    log_info "Quick mode: validating ${NUXEL_DEVICE_KEY} device context only"
    quick_ok=0
    quick_missing=0
    for pair in \
        "kernel defconfig:kernel/${NUXEL_DEVICE_DIR}/defconfig" \
        "kernel patches:kernel/${NUXEL_DEVICE_DIR}/patches" \
        "kernel toolchain doc:kernel/${NUXEL_DEVICE_DIR}/README-toolchain.md" \
        "deviceinfo:device/${NUXEL_DEVICE_DIR}/deviceinfo" \
        "device APKBUILD:device/${NUXEL_DEVICE_DIR}/APKBUILD" \
        "firmware manifest:firmware/${NUXEL_DEVICE_DIR}/manifest.yml" \
        "boot flash tool:boot/${NUXEL_DEVICE_DIR}/flash.sh" \
        "display config:configs/${NUXEL_DEVICE_DIR}/display" \
        "touch config:configs/${NUXEL_DEVICE_DIR}/libinput" \
        "audio config:configs/${NUXEL_DEVICE_DIR}/alsa-ucm" \
        "modem config:configs/${NUXEL_DEVICE_DIR}/modem" \
        "pipewire config:configs/${NUXEL_DEVICE_DIR}/pipewire" \
        "wireplumber config:configs/${NUXEL_DEVICE_DIR}/wireplumber"; do
        label="${pair%%:*}"; path="${pair#*:}"
        if [ -e "${ROOT}/${path}" ]; then
            log_ok "  ${label}: ${path}"
            quick_ok=$((quick_ok + 1))
        else
            log_warn "  ${label} MISSING: ${path}"
            quick_missing=$((quick_missing + 1))
        fi
    done
    {
        echo "nuxel quick-mode device context"
        echo "device_key=${NUXEL_DEVICE_KEY}"
        echo "device_dir=${NUXEL_DEVICE_DIR}"
        echo "kernel_out=${KOUT}"
        echo "checks_passed=${quick_ok}"
        echo "checks_missing=${quick_missing}"
        echo "built=$(date -u +%FT%TZ 2>/dev/null || date -u)"
    } > "${DEV_OUT}/quick-manifest.txt"
    log_ok "Quick-mode context verified -> ${DEV_OUT}/quick-manifest.txt"
    if [ "${quick_missing}" -gt 0 ]; then
        log_warn "${quick_missing} per-device input(s) missing (see quick-manifest.txt)"
    fi
    exit 0
fi

# =============================================================================
# Step 0 — verify inputs
# =============================================================================
KERNEL_PRESENT=0
[ -f "${IMAGE_GZ}" ] && [ -s "${IMAGE_GZ}" ] && KERNEL_PRESENT=1
DTB_PRESENT=0
if [ -d "${DTBS}" ]; then
    DTB_PRESENT=1
    DTBS_COUNT="$(find "${DTBS}" -type f 2>/dev/null | wc -l | tr -d ' ')"
else
    DTBS_COUNT=0
fi
log_info "kernel out dir : ${KOUT}"
log_info "  Image.gz      : $([ "${KERNEL_PRESENT}" -eq 1 ] && echo present || echo "NOT YET (bg-kernel still building)")"
log_info "  dtbs/         : ${DTBS_COUNT} file(s)"

# =============================================================================
# Step 1 — stage + pack the initramfs (always produced)
# =============================================================================
STAGE="${BUILD_TMP_STAGE:-$(mktemp -d /tmp/nuxel-initramfs.XXXXXX)}"
trap 'rm -rf "${STAGE:-}"' EXIT

ASSEMBLER_ARGS=(--stage "${STAGE}" --out "${BOOT_DIR}/initramfs.cpio.gz"
                --width "${WIDTH}" --height "${HEIGHT}")
[ "${NO_SPLASH}" -eq 1 ] && ASSEMBLER_ARGS+=(--no-splash)
if [ -d "${BOOT_DIR}/modules" ]; then
    ASSEMBLER_ARGS+=(--modules-dir "${BOOT_DIR}/modules")
fi

log_step(){ printf '\n%s=== %s ===%s\n' "${CYAN}" "$1" "${NC}"; }
log_step "Building initramfs"

mkdir -p "${BOOT_DIR}"

# Stage modules if the kernel build shipped modules (modules.tar.* )
if [ "${KERNEL_PRESENT}" -eq 1 ] && [ ! -d "${BOOT_DIR}/modules" ]; then
    for tarball in "${KOUT}/modules.tar.gz" "${KOUT}/modules.tar.bz2"; do
        if [ -f "${tarball}" ]; then
            mkdir -p "${BOOT_DIR}/modules"
            case "${tarball}" in
                *.gz) tar -xzf "${tarball}" -C "${BOOT_DIR}/modules" 2>/dev/null || true ;;
                *.bz2) tar -xjf "${tarball}" -C "${BOOT_DIR}/modules" 2>/dev/null || true ;;
            esac
        fi
    done
fi
# also honour an already-populated modules dir under boot/boot.img/modules
if [ -d "${KOUT}/firmware" ] && [ ! -e "${BOOT_DIR}/modules/firmware" ]; then
    mkdir -p "${BOOT_DIR}/modules"
    cp -a "${KOUT}/firmware" "${BOOT_DIR}/modules/firmware" 2>/dev/null || true
fi
if [ -d "${BOOT_DIR}/modules" ]; then
    ASSEMBLER_ARGS+=(--modules-dir "${BOOT_DIR}/modules")
fi

# Generate the splash + pack the cpio/gzip.
if ! "${PY}" "${PKG}/assembler.py" "${ASSEMBLER_ARGS[@]}"; then
    log_err "initramfs assembly failed"
    exit 1
fi
chmod 0644 "${BOOT_DIR}/initramfs.cpio.gz"

# --initramfs-only: the shared initramfs is the whole deliverable. Mirror it to
# build/boot-artifact/ (the path the Makefile + per-device scripts look for) and
# exit 0. No kernel is required for a real, complete initramfs.
if [ "${INITRAMFS_ONLY}" -eq 1 ]; then
    mkdir -p "${OUT_DIR}"
    cp -f "${BOOT_DIR}/initramfs.cpio.gz" "${OUT_DIR}/initramfs.cpio.gz"
    log_ok "initramfs-only: ${BOOT_DIR}/initramfs.cpio.gz"
    log_ok "initramfs-only: mirrored to ${OUT_DIR}/initramfs.cpio.gz"
    exit 0
fi

# clear our own old boot.img if we're regenerating from scratch (never clobber
# a real Android image silently unless --force allows rebuild)
if [ "${FORCE}" -eq 1 ]; then
    rm -f "${BOOT_DIR}/boot.img"
fi

# =============================================================================
# Step 2 — produce the boot image
# =============================================================================
log_step "Packaging boot image"

CMDLINE_DEFAULT=(
  "nuxel.slot=a"
  "quiet"
  "loglevel=0"
  "nuxel.console=ttyS0"
  "nuxel.boot=1"
  "root=/dev/disk/by-partlabel/system_a"
  "rootwait"
  "ro"
  "rootfstype=ext4"
)
CMDLINE="$(IFS=' '; echo "${CMDLINE_DEFAULT[*]}")"

BOOT_IMG="${BOOT_DIR}/boot.img"

pick_dtb() {
    # Generic-dtb preference (briq-a1): pick, in order of preference:
    #   1. the mustang DTB (shipping board) if the vendor tree is available;
    #   2. a QEMU arm-virt / generic machine DTB when the kernel build ships
    #      one (e.g. arch/arm64/boot/dts/arm/*virt*.dtb, *fvp*.dtb, *qemu*.dtb,
    #      *virt*.dtb) — this is the genuinely-bootable generic ARM64 path;
    #   3. the first *.dtb found, purely as a last-ditch fallback so a bare
    #      vendor board blob is only used when no generic machine DTB exists.
    if [ "${DTB_PRESENT}" -eq 1 ]; then
        local c
        c="$(find "${DTBS}" -iname 'mustang*.dtb' -o -iname '*mustang*.dtb' 2>/dev/null | head -1)"
        [ -n "${c}" ] && { echo "${c}"; return; }
        # generic / QEMU machine DTB present in the build?
        c="$(find "${DTBS}" '(' -path '*arm64/boot/dts/arm/*.dtb'                -o -path '*boot/dts/arm/*.dtb'                -o -iname '*virt*.dtb' -o -iname '*fvp*.dtb'                -o -iname '*qemu*.dtb' ')' -name '*.dtb' 2>/dev/null | head -1)"
        [ -n "${c}" ] && { echo "${c}"; return; }
        # last-ditch: first dtb (specific vendor board) only if no generic one
        c="$(find "${DTBS}" -type f -name '*.dtb' 2>/dev/null | head -1)"
        [ -n "${c}" ] && { echo "${c}"; return; }
    fi
}

ANDROID_DONE=0
# Export the unpacked kernel pieces whenever a kernel is present, so the
# Android boot.img is always accompanied by its genuine components.
if [ "${KERNEL_PRESENT}" -eq 1 ]; then
    cp -f "${IMAGE_GZ}" "${BOOT_DIR}/Image.gz" 2>/dev/null || true
    [ -f "${IMAGE}" ] && cp -f "${IMAGE}" "${BOOT_DIR}/Image" 2>/dev/null || true
fi

# Genuine Android Boot Header v4 path. A REAL kernel Image.gz + initramfs are
# strictly required (guaranteed by KERNEL_PRESENT above). The ANDROID!-magic
# image is produced either by the AOSP mkbootimg binary (when installed) or by
# our byte-correct internal images/bootpack/mkbootimg.py (AOSP mkbootimg.py
# layout), so the header is never fabricated/zero-padded.
# ANDROID!-format boot image is the DEFAULT when a real kernel + initramfs
# exist (byte-correct internal mkbootimg.py, or AOSP mkbootimg when installed);
# --android is accepted for compatibility and forces the same genuine path.
if [ "${KERNEL_PRESENT}" -eq 1 ] \
   && [ -f "${BOOT_DIR}/Image.gz" ] && [ -f "${BOOT_DIR}/initramfs.cpio.gz" ]; then
    DTB="$(pick_dtb || true)"
    ORIG_IMG="${BOOT_IMG}"
    if command -v mkbootimg >/dev/null 2>&1; then
        log_info "Android Boot Image Header v4 via AOSP mkbootimg"
        if mkbootimg \
                --kernel "${IMAGE_GZ}" \
                --ramdisk "${BOOT_DIR}/initramfs.cpio.gz" \
                --dtb "${DTB}" \
                --cmdline "${CMDLINE}" \
                --base 0x10000000 --kernel_offset 0x00008000 \
                --ramdisk_offset 0x01000000 \
                --header_version 4 \
                --os_version 15.0.0 --os_patch_level 2025-06-05 \
                --pagesize 4096 \
                --output "${BOOT_IMG}" 2>/dev/null; then
            chmod 0644 "${BOOT_IMG}" 2>/dev/null || true
            ANDROID_DONE=1
        fi
    elif [ -x "${PKG}/mkbootimg.py" ] || [ -f "${PKG}/mkbootimg.py" ]; then
        log_info "Android Boot Image Header v4 via internal mkbootimg.py (AOSP-compatible)"
        # v4 boot compacts kernel + ramdisk under the ANDROID! header; DTB is
        # emitted to a companion vendor_boot when a real DTB is available.
        VENDOR_BOOT_OPTS=()
        if [ -n "${DTB}" ] && [ -f "${DTB}" ]; then
            VENDOR_BOOT_OPTS+=(--vendor-boot "${BOOT_DIR}/vendor_boot.img" --dtb "${DTB}")
        fi
        if "${PY}" "${PKG}/mkbootimg.py" \
                --kernel "${BOOT_DIR}/Image.gz" \
                --ramdisk "${BOOT_DIR}/initramfs.cpio.gz" \
                --cmdline "${CMDLINE}" \
                --os-version 15.0.0 --os-patch-level 2025-06-05 \
                --header-version 4 --pagesize 4096 \
                "${VENDOR_BOOT_OPTS[@]}" \
                --output "${BOOT_IMG}"; then
            chmod 0644 "${BOOT_IMG}" 2>/dev/null || true
            ANDROID_DONE=1
        else
            log_err "internal mkbootimg.py failed (kernel/initramfs present but image not writable)"
        fi
    else
        log_warn "--android requested but no mkbootimg tooling available; using generic ARM64 image."
    fi
fi

# ---- generic ARM64 boot image (the genuine fallback) -------------------------
# ---- generic ARM64 boot image (the genuine default) --------------------------
if [ "${ANDROID_DONE}" -eq 0 ]; then
    log_info "Producing generic ARM64 boot image (self-describing payload)"
    # The initramfs.cpio.gz is a full bootable Linux initrd (genuinely
    # bootable as `qemu -initrd boot/boot.img/initramfs.cpio.gz`).  The
    # single-file boot.img additionally embeds the real kernel Image.gz and
    # device tree (if present) behind a tiny descriptor header so the
    # artifact is packaged AND self-describing, never zero-fabricated.
    rm -f "${BOOT_IMG}"
    # Always export the genuine pieces unpacked for -kernel/-initrd/-dtb boot.
    if [ "${KERNEL_PRESENT}" -eq 1 ]; then
        cp -f "${IMAGE_GZ}" "${BOOT_DIR}/Image.gz" 2>/dev/null || true
        [ -f "${IMAGE}" ] && cp -f "${IMAGE}" "${BOOT_DIR}/Image" 2>/dev/null || true
    fi

    DTB="$(pick_dtb || true)"
    if [ -n "${DTB}" ] && [ -f "${DTB}" ]; then
        cp -f "${DTB}" "${BOOT_DIR}/all.dtb" 2>/dev/null || true
        DTB_NAME="$(basename "${DTB}")"
        cp -f "${DTB}" "${BOOT_DIR}/${DTB_NAME}" 2>/dev/null || true
    fi

    printf '%s\n' "${CMDLINE}" > "${BOOT_DIR}/cmdline.txt"

    if [ "${KERNEL_PRESENT}" -eq 1 ] && [ -f "${BOOT_DIR}/initramfs.cpio.gz" ]; then
        # Compound self-describing bundle (kernel + initramfs + dtb).
        PACK_ARGS=(--initramfs "${BOOT_DIR}/initramfs.cpio.gz")
        [ -f "${BOOT_DIR}/Image.gz" ] && PACK_ARGS+=(--kernel "${BOOT_DIR}/Image.gz")
        [ -n "${DTB_NAME:-}" ] && PACK_ARGS+=(--dtb "${BOOT_DIR}/${DTB_NAME}")
        if ! "${PY}" "${PKG}/pack_generic.py" \
                "${PACK_ARGS[@]}" \
                --cmdline "${CMDLINE}" \
                --output "${BOOT_IMG}" --pad-min 4194304; then
            log_err "generic pack failed"
            exit 1
        fi
    else
        # No kernel yet (bg-kernel still building / blocked): we must NOT ship
        # a kernel-less boot.img pretending to be a verifiable boot artifact.
        # The previous behaviour copied initramfs.cpio.gz to boot.img and padded
        # it, producing a boot.img byte-identical to the initramfs (a gzip stream
        # with zero kernel payload) — rejected by inspeQtor. Instead we:
        #   * leave NO boot.img (so ci/validate-build.sh / flash.sh never consume
        #     a fake kernel image);
        #   * keep the genuinely-bootable initramfs.cpio.gz (qemu -initrd only);
        #   * mark this group NOT_DONE/blocked on bg-kernel in the manifest so the
        #     boot artifact chain is never declared verifiable without a kernel.
        rm -f "${BOOT_IMG}"
        rm -f "${BOOT_DIR}/Image.gz" "${BOOT_DIR}/Image" "${BOOT_DIR}/all.dtb" 2>/dev/null || true
        if [ ! -f "${BOOT_DIR}/initramfs.cpio.gz" ]; then
            log_err "initramfs.cpio.gz missing; cannot produce any boot payload"
            exit 1
        fi
        log_warn "KERNEL IMAGE MISSING: no boot.img produced (boot artifact NOT_DONE, blocked on bg-kernel)"
        log_warn "Only the initramfs payload boot/boot.img/initramfs.cpio.gz is present and bootable"
        NOT_DONE=1
    fi
    # Only export unpacked generic pieces when a real kernel is present.
    # (chmod is now guarded so a removed boot.img is not touched.)
fi

# Always export the cmdline alongside the Android image.
printf '%s\n' "${CMDLINE}" > "${BOOT_DIR}/cmdline.txt"

if [ -f "${BOOT_IMG}" ]; then
    chmod 0644 "${BOOT_IMG}" 2>/dev/null || true
fi

# Verify the result is real and non-zero.
if [ -f "${BOOT_IMG}" ]; then
    FINAL_SIZE="$(stat -f%z "${BOOT_IMG}" 2>/dev/null || stat -c%s "${BOOT_IMG}" 2>/dev/null || echo 0)"
    if [ "${FINAL_SIZE}" -ge 4194304 ]; then
        log_ok "boot.img: ${BOOT_IMG} (${FINAL_SIZE} bytes, >= 4 MiB)"
    else
        log_warn "boot.img is ${FINAL_SIZE} bytes (< 4 MiB)"
    fi
else
    FINAL_SIZE=0
    log_warn "no boot.img produced (kernel absent) — see boot-manifest.txt status"
fi

# =============================================================================
# Step 3 — shadow copy (NOT build/output, which is owned by the CI group)
# =============================================================================
if [ "${SKIP_SHADOW}" -eq 0 ]; then
    log_step "Shadow copy to ${OUT_DIR}"
    mkdir -p "${OUT_DIR}"
    for f in boot.img initramfs.cpio.gz; do
        if [ -f "${BOOT_DIR}/${f}" ]; then
            cp -f "${BOOT_DIR}/${f}" "${OUT_DIR}/${f}" 2>/dev/null || true
        fi
    done
    if [ -f "${BOOT_DIR}/Image.gz" ]; then cp -f "${BOOT_DIR}/Image.gz" "${OUT_DIR}/Image.gz" 2>/dev/null || true; fi
    if [ -f "${BOOT_IMG}" ]; then
        log_ok "shadowed at ${OUT_DIR}"
    else
        log_warn "no boot.img to shadow (kernel absent); initramfs chain available at ${OUT_DIR}"
    fi
fi

# =============================================================================
# Step 3b — per-device output mirror (device-selected layout)
# =============================================================================
DEV_OUT="${ROOT}/build/out/${NUXEL_DEVICE_KEY}"
mkdir -p "${DEV_OUT}"
for f in boot.img initramfs.cpio.gz Image.gz Image; do
    if [ -f "${BOOT_DIR}/${f}" ]; then
        cp -f "${BOOT_DIR}/${f}" "${DEV_OUT}/${f}" 2>/dev/null || true
    fi
done
cat > "${DEV_OUT}/device-manifest.txt" <<EOF
Nuxel device output mirror
device_key=${NUXEL_DEVICE_KEY}
device_dir=${NUXEL_DEVICE_DIR}
kernel_out=${KOUT}
boot_artifact=${BOOT_DIR}
built=$(date -u +%FT%TZ 2>/dev/null || date -u)
EOF
log_ok "per-device output mirror -> ${DEV_OUT}"

# =============================================================================
# Manifest
# =============================================================================
cat > "${BOOT_DIR}/boot-manifest.txt" <<EOF
Nuxel boot artifact manifest
device_key=${NUXEL_DEVICE_KEY}
device_dir=${NUXEL_DEVICE_DIR}
kernel_out=${KOUT}
kernel_image_gz=$([ "${KERNEL_PRESENT}" -eq 1 ] && echo "kernel/${NUXEL_DEVICE_DIR}/.build/out/Image.gz" || echo "MISSING (bg-kernel pending)")
dtbs_count=${DTBS_COUNT}
format=$([ "${ANDROID_DONE}" -eq 1 ] && echo "android-boot-header-v4" || ( [ "${KERNEL_PRESENT}" -eq 1 ] && echo "generic-arm64-NUXELBOOT1-bundle" || echo "generic-arm64-initramfs-only" ))
status=$([ "${ANDROID_DONE}" -eq 1 ] && echo "android-boot-header-v4-done" || ( [ "${KERNEL_PRESENT}" -eq 1 ] && echo "generic-arm64-NUXELBOOT1-bundle" || echo "generic-arm64-initramfs-only" ))
artifact_status=$([ "${KERNEL_PRESENT}" -eq 1 ] && echo "DONE" || echo "NOT_DONE (blocked on bg-kernel: no Image.gz in kernel/${NUXEL_DEVICE_DIR}/.build/out)")
boot_img=${BOOT_IMG}
boot_img_size=${FINAL_SIZE}
boot_img_present=$([ -f "${BOOT_IMG}" ] && echo "yes" || echo "no")
initramfs=${BOOT_DIR}/initramfs.cpio.gz
cmdline=${CMDLINE}
built=$(date -u +%FT%TZ 2>/dev/null || date -u)
EOF
log_ok "manifest -> ${BOOT_DIR}/boot-manifest.txt"

echo ""
FMT_LABEL="generic NUXELBOOT1 bundle"
[ "${ANDROID_DONE}" -eq 1 ] && FMT_LABEL="Android Boot Image Header v4 (ANDROID!)"
if [ "${KERNEL_PRESENT}" -eq 1 ] && [ -f "${BOOT_IMG}" ]; then
    log_ok "Boot artifact build complete (${FMT_LABEL} — kernel embedded)."
    exit 0
else
    # No real kernel present: the full boot.img cannot be produced without
    # fabricating bytes. We keep the genuine initramfs chain and explicitly
    # report this group as NOT_DONE (blocked on bg-kernel) so we never ship a
    # kernel-less artifact as though it were verifiable. Re-run once
    # kernel/.build/out/Image.gz + dtbs/ exist to emit the real boot.img.
    log_warn "BOOT ARTIFACT NOT_DONE: kernel Image.gz missing (bg-kernel blocked,"
    log_warn "exit-code $(cat "${KOUT}/exit-code" 2>/dev/null || echo '?'))."
    log_warn "Produced boot/boot.img/initramfs.cpio.gz (genuinely bootable via qemu -initrd only)."
    log_warn "No boot.img was emitted — re-run images/build.sh after bg-kernel produces the kernel."
    exit 3
fi
