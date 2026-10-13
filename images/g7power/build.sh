#!/usr/bin/env bash
# =============================================================================
# Nuxel G7 Power Rootfs/Boot Build Orchestration — Motorola Moto G7 Power
# (g7power, ocean, Snapdragon 632 / SDM632, msm8953 family)
#
# Assembles the G7 Power boot images and rootfs image under build/out/g7power/:
#   * nuxel-ocean-boot.img    (Nuxel kernel + initramfs + DTB as a v1 boot.img)
#   * nuxel-ocean-rootfs.img  (ext4 rootfs for the userdata partition)
#   * lk2nd.img               (copy of the lk2nd msm8953 build, if present)
#   * build-manifest.json     (device key, kernel commit, build timestamp)
#
# Usage:
#   NUXEL_DEVICE=g7power bash images/g7power/build.sh [--device g7power] [--help]
#
# Inputs required (abort with a clear message when missing):
#   * kernel/g7power/.build/out/arch/arm64/boot/Image.gz   (build-kernel.sh)
#   * sdm632-motorola-ocean.dtb under
#     kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/  (build-kernel.sh)
#   * a shared initramfs: first existing of boot/initramfs/,
#     boot/boot.img/, build/boot-artifact/ (see --help for the search order)
#
# Phase 1 emits NO dm-verity/AVB image on purpose: the bring-up rootfs must
# stay writable (ABOOT -> lk2nd -> mainline Linux -> initramfs -> rootfs is
# not yet stable enough for a verified-boot chain). dm-verity/AVB is a later
# phase. Phase 0 device inventory (docs/g7power-device-inventory.md) must be
# filled before a real build; --help is exempt.
#
# This script is device-isolated: it only ever writes under build/out/g7power/
# (plus the shared images/mkrootfs.sh staging dir build/out/rootfs) and never
# touches any other device target's build output tree, and it never flashes
# anything to a device (see boot/g7power/flash.sh).
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

log()  { echo "[nuxel-g7power-build] $*"; }
warn() { echo "[nuxel-g7power-build][warn] $*" >&2; }
err()  { echo "[nuxel-g7power-build][error] $*" >&2; }

usage() {
    cat <<'EOF'
Usage: NUXEL_DEVICE=g7power bash images/g7power/build.sh [--device g7power] [--help]

Builds the G7 Power (ocean, SDM632/msm8953) boot + rootfs artifacts into
build/out/g7power/:

  nuxel-ocean-boot.img    linux-postmarketos-qcom-msm8953 Image.gz +
                          initramfs + sdm632-motorola-ocean.dtb as a legacy
                          Android boot image (header v1, page 2048)
  nuxel-ocean-rootfs.img  ext4 rootfs image (for the userdata partition)
  lk2nd.img               lk2nd msm8953 build (copied from
                          boot/g7power/lk2nd/.build/build-msm8953/lk2nd.img)
  build-manifest.json     device key, kernel commit, build timestamp

Required inputs (abort if missing):
  kernel/g7power/.build/out/arch/arm64/boot/Image.gz   (build-kernel.sh)
  sdm632-motorola-ocean.dtb under
    kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/ (build-kernel.sh)
  shared initramfs (first existing of):
    boot/initramfs/initramfs.cpio.gz                   (spec path)
    boot/boot.img/initramfs.cpio.gz                    (images/build.sh output)
    build/boot-artifact/initramfs.cpio.gz              (Makefile consolidation)

The G7 Power boot chain is PBL -> stock ABOOT -> lk2nd -> mainline Linux ->
Nuxel initramfs -> rootfs (A-only eMMC, no A/B slots, no vendor_boot /
init_boot / vbmeta / fastbootd super partition). Flash order is enforced by
boot/g7power/flash.sh (dtbo MUST be flashed before lk2nd — classic msm8953
soft-brick). This script only builds artifacts and never flashes a device.

Phase 1 emits NO dm-verity/AVB image: the bring-up rootfs stays writable
during bring-up; verified boot is a later phase. Phase 0 device inventory
(docs/g7power-device-inventory.md) must be filled before a real build;
--help is exempt.

This script is device-isolated: it only ever writes under build/out/g7power/
and never touches any other device target's build output.
EOF
}

# --help exits before any gate work (device selection + inventory gate).
for arg in "$@"; do
    case "$arg" in
        --help|-h) usage; exit 0 ;;
    esac
done

# ---------------------------------------------------------------------------
# Device guard — G7 Power only. Explicit selection required (env or --device);
# the shared selector never silently guesses. After this guard,
# ${NUXEL_DEVICE_DIR} is "g7power" and every per-device path below is
# derived from it, so no other device's tree can be touched.
# ---------------------------------------------------------------------------
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "g7power" ] || {
    err "images/g7power/build.sh is ONLY for g7power. Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

# Per-device tree (selector-verified: == g7power).
DEVICE_DIR="${NUXEL_DEVICE_DIR}"
KERNEL_OUT="${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/out"
KSRC="${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/src"
LK2ND_BUILD_DIR="${NUXEL_ROOT}/boot/${DEVICE_DIR}/lk2nd/.build/build-msm8953"
BOOT_OUT="${NUXEL_ROOT}/build/out/${DEVICE_DIR}"
ROOTFS_STAGING="${NUXEL_ROOT}/build/out/rootfs"   # images/mkrootfs.sh staging dir
PACKER="${NUXEL_ROOT}/boot/${DEVICE_DIR}/pack-boot-v1.sh"

# ---------------------------------------------------------------------------
# Inventory gate (Phase 0) — see docs/g7power-device-inventory.md.
# Blocks real build operations until the operator has filled the critical
# fields (KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAMES) from the
# physical device. Never blocks --help (handled above).
# ---------------------------------------------------------------------------
_check_g7power_inventory() { local inv="${NUXEL_ROOT}/docs/g7power-device-inventory.md"; [ -f "${inv}" ] || { echo "ERROR: docs/g7power-device-inventory.md missing — run Phase 0 inventory first."; exit 1; }; if grep -qE "KERNEL_ADDR:.*PLACEHOLDER|RAMDISK_ADDR:.*PLACEHOLDER|TAGS_ADDR:.*PLACEHOLDER|WIFI_FW_FILENAMES:.*UNKNOWN" "${inv}"; then echo "ERROR: G7 Power device inventory incomplete."; echo "       Run Phase 0 commands in docs/g7power-device-inventory.md"; echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, WIFI_FW_FILENAMES"; exit 1; fi; }
_check_g7power_inventory

# --- 1. Required inputs ----------------------------------------------------
KERNEL_IMG="${KERNEL_OUT}/arch/arm64/boot/Image.gz"
[ -f "${KERNEL_IMG}" ] || {
    err "Kernel image not found: ${KERNEL_IMG}"
    err "Run: NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone"
    exit 1
}

# The G7 Power DTB lives under .../arch/arm64/boot/dts/qcom/ (mainline msm8953
# tree: qcom/sdm632-motorola-ocean.dtb). find(1) is used instead of a shell
# glob so the search is quiet and deterministic even when no DTB exists yet.
DTB="$(find "${KERNEL_OUT}/arch/arm64/boot/dts/qcom" -maxdepth 1 \
    -name 'sdm632-motorola-ocean.dtb' -print -quit 2>/dev/null || true)"
[ -n "${DTB}" ] || {
    err "No sdm632-motorola-ocean.dtb found under ${KERNEL_OUT}/arch/arm64/boot/dts/qcom/"
    err "Run: NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone"
    exit 1
}

# Shared initramfs: produced by the shared boot-image pipeline. The spec path
# boot/initramfs/initramfs.cpio.gz is tried first, then the actual shared
# pipeline outputs (images/build.sh writes boot/boot.img/initramfs.cpio.gz and
# the Makefile consolidates it under build/boot-artifact/). Abort only if none
# of the three exists.
INITRAMFS=""
for _candidate in \
    "${NUXEL_ROOT}/boot/initramfs/initramfs.cpio.gz" \
    "${NUXEL_ROOT}/boot/boot.img/initramfs.cpio.gz" \
    "${NUXEL_ROOT}/build/boot-artifact/initramfs.cpio.gz"; do
    if [ -f "${_candidate}" ]; then
        INITRAMFS="${_candidate}"
        break
    fi
done
[ -n "${INITRAMFS}" ] || {
    err "Shared initramfs not found (tried boot/initramfs/initramfs.cpio.gz, boot/boot.img/initramfs.cpio.gz, build/boot-artifact/initramfs.cpio.gz)"
    err "It is produced by the shared boot-image pipeline (images/build.sh)."
    exit 1
}
log "Using shared initramfs: ${INITRAMFS}"

mkdir -p "${BOOT_OUT}"
log "Building G7 Power artifacts into ${BOOT_OUT}"

# --- 1b. Phase-0 inventory load addresses ----------------------------------
# The gate above guarantees KERNEL_ADDR/RAMDISK_ADDR/TAGS_ADDR are filled, so
# feed the inventoried (device-derived) values to the packer — otherwise every
# post-inventory build would silently use the packer's PLACEHOLDER defaults.
INVENTORY="${NUXEL_ROOT}/docs/g7power-device-inventory.md"
INV_ADDR_KERNEL="$(awk '/^KERNEL_ADDR:/{print $2; exit}' "${INVENTORY}")"
INV_ADDR_RAMDISK="$(awk '/^RAMDISK_ADDR:/{print $2; exit}' "${INVENTORY}")"
INV_ADDR_TAGS="$(awk '/^TAGS_ADDR:/{print $2; exit}' "${INVENTORY}")"
PACK_ADDR_ARGS=()
if [[ "${INV_ADDR_KERNEL}" =~ ^0x[0-9a-fA-F]+$ ]]; then
    PACK_ADDR_ARGS+=(--kernel-addr "${INV_ADDR_KERNEL}")
else
    warn "KERNEL_ADDR ('${INV_ADDR_KERNEL}') is not a hex address in ${INVENTORY}; falling back to packer default."
fi
if [[ "${INV_ADDR_RAMDISK}" =~ ^0x[0-9a-fA-F]+$ ]]; then
    PACK_ADDR_ARGS+=(--ramdisk-addr "${INV_ADDR_RAMDISK}")
else
    warn "RAMDISK_ADDR ('${INV_ADDR_RAMDISK}') is not a hex address in ${INVENTORY}; falling back to packer default."
fi
if [[ "${INV_ADDR_TAGS}" =~ ^0x[0-9a-fA-F]+$ ]]; then
    PACK_ADDR_ARGS+=(--tags-addr "${INV_ADDR_TAGS}")
else
    warn "TAGS_ADDR ('${INV_ADDR_TAGS}') is not a hex address in ${INVENTORY}; falling back to packer default."
fi
if [ ${#PACK_ADDR_ARGS[@]} -eq 0 ]; then
    err "No real load addresses available from ${INVENTORY} — refusing to emit images with the packer PLACEHOLDER defaults."
    err "Fill KERNEL_ADDR/RAMDISK_ADDR/TAGS_ADDR from the real device stock boot.img before flashing."
    exit 1
fi

# --- 2. Boot image via boot/g7power/pack-boot-v1.sh ------------------------
# Legacy Android boot image header v1 (page 2048, ANDROID! magic) — the format
# ABOOT/lk2nd reads on the G7 Power (A-only, no vendor_boot/init_boot/vbmeta).
# Load addresses come from Phase 0 inventory; the packer prints a warning and
# supports --addresses-from-device for values extracted from the stock boot.img.
CMDLINE="console=ttyMSM0,115200 earlycon=msm_geni_serial,0xa88000 nuxel.device=g7power root=/dev/block/bootdevice/by-name/userdata rootfstype=ext4 rootwait rw"

log "Packing Nuxel boot image (kernel + initramfs + DTB, v1 header)..."
python3 "${PACKER}" \
    --kernel "${KERNEL_IMG}" \
    --ramdisk "${INITRAMFS}" \
    --dtb "${DTB}" \
    --cmdline "${CMDLINE}" \
    "${PACK_ADDR_ARGS[@]}" \
    --output "${BOOT_OUT}/nuxel-ocean-boot.img"

# --- 3. Userspace rootfs via the device-agnostic builder --------------------
# images/mkrootfs.sh is the shared, device-agnostic userspace builder
# (Flatpak runtime + Nuxel services/apps/security configs). It is invoked
# as-is and populates build/out/rootfs (and, when its bake step runs,
# build/out/system.img). OpenRC is the phone-target init (pmOS-style).
log "Assembling Nuxel userspace with images/mkrootfs.sh (device-agnostic)..."
export NUXEL_INIT="${NUXEL_INIT:-openrc}"
bash "${NUXEL_ROOT}/images/mkrootfs.sh"

# --- 4. Overlay device-specific content into the rootfs staging ------------
# All G7 Power content is installed AFTER the shared userspace build so
# nothing device-specific ever leaks into the shared pipeline.

if [ -d "${NUXEL_ROOT}/firmware/${DEVICE_DIR}/blobs" ]; then
    log "Installing G7 Power firmware blobs into rootfs staging..."
    # --install honors the manifest's required/pending logic; --force-pending
    # lets already-pulled blobs land while UNKNOWN-checksum entries are only
    # reported (never fatal) during bring-up. The script self-guards on
    # NUXEL_DEVICE_KEY==g7power and aborts before Phase 0 inventory is filled,
    # so failures here are expected pre-inventory and are non-fatal for the
    # boot images (the rootfs just ships without firmware until then).
    NUXEL_DEVICE=g7power bash "${NUXEL_ROOT}/firmware/${DEVICE_DIR}/install-firmware.sh" \
        --install --force-pending --rootfs-staging "${ROOTFS_STAGING}" || \
        warn "firmware install reported pending/missing blobs (expected pre-Phase-0)."
else
    warn "firmware/${DEVICE_DIR}/blobs not present — run --adb-pull on the G7 Power first."
fi

if [ -d "${NUXEL_ROOT}/configs/${DEVICE_DIR}" ]; then
    log "Installing G7 Power device configs into rootfs staging..."
    mkdir -p "${ROOTFS_STAGING}/etc/nuxel/device/${DEVICE_DIR}"
    cp -a "${NUXEL_ROOT}/configs/${DEVICE_DIR}/." "${ROOTFS_STAGING}/etc/nuxel/device/${DEVICE_DIR}/"
    if [ -f "${NUXEL_ROOT}/device/${DEVICE_DIR}/90-nuxel-ocean.rules" ]; then
        mkdir -p "${ROOTFS_STAGING}/etc/udev/rules.d"
        cp -a "${NUXEL_ROOT}/device/${DEVICE_DIR}/90-nuxel-ocean.rules" \
            "${ROOTFS_STAGING}/etc/udev/rules.d/"
    fi
    if [ -f "${NUXEL_ROOT}/device/${DEVICE_DIR}/nuxel-ocean.conf" ]; then
        mkdir -p "${ROOTFS_STAGING}/etc/nuxel"
        cp -a "${NUXEL_ROOT}/device/${DEVICE_DIR}/nuxel-ocean.conf" \
            "${ROOTFS_STAGING}/etc/nuxel/"
    fi
else
    warn "configs/${DEVICE_DIR} not present — G7 Power display/audio/touch configs skipped."
fi

# Kernel modules: primary location per the spec is
# kernel/g7power/.build/modules-staging/lib/modules (INSTALL_MOD_PATH=<.build/
# modules-staging> in build-kernel.sh); also accept .build/out/lib/modules for
# module-install workflows that install into the kernel output tree.
KERNEL_MODULES_DIR=""
if [ -d "${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/modules-staging/lib/modules" ]; then
    KERNEL_MODULES_DIR="${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/modules-staging/lib/modules"
elif [ -d "${KERNEL_OUT}/lib/modules" ]; then
    KERNEL_MODULES_DIR="${KERNEL_OUT}/lib/modules"
fi
if [ -n "${KERNEL_MODULES_DIR}" ]; then
    log "Installing G7 Power kernel modules into rootfs staging (/lib/modules)..."
    mkdir -p "${ROOTFS_STAGING}/lib/modules"
    cp -a "${KERNEL_MODULES_DIR}/." "${ROOTFS_STAGING}/lib/modules/"
else
    warn "No kernel modules found (checked ${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/modules-staging/lib/modules and ${KERNEL_OUT}/lib/modules). Skipped."
    warn "Produce them with:"
    warn "  make -C \"${KSRC}\" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \\"
    warn "       O=\"${KERNEL_OUT}\" modules_install INSTALL_MOD_PATH=\"${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/modules-staging\""
fi

# --- 5. Emit rootfs image ---------------------------------------------------
# Phase 1: plain ext4, writable. NO dm-verity/AVB yet — the bring-up rootfs
# must stay writable (ABOOT -> lk2nd -> mainline Linux -> initramfs -> rootfs
# is not stable enough for a verified-boot chain); dm-verity/AVB is deferred
# to a later phase. The image is baked from the final staging dir so the G7
# Power firmware, configs and kernel modules are included.
_bake_rootfs_image() {
    local rootfs_img="${BOOT_OUT}/nuxel-ocean-rootfs.img"
    local size_m img_m

    if [ ! -d "${ROOTFS_STAGING}" ] || [ -z "$(ls -A "${ROOTFS_STAGING}" 2>/dev/null || true)" ]; then
        # Staging empty (mkrootfs produced nothing) — fall back to a
        # pre-baked shared system.img when one exists.
        if [ -f "${NUXEL_ROOT}/build/out/system.img" ]; then
            cp -a "${NUXEL_ROOT}/build/out/system.img" "${rootfs_img}"
            log "Rootfs image: ${rootfs_img} (copy of build/out/system.img; NO dm-verity Phase 1)"
            warn "build/out/system.img was baked before the G7 Power overlays — re-run with a"
            warn "populated mkrootfs staging to include firmware/configs/modules in the image."
            return 0
        fi
        warn "Rootfs staging empty and build/out/system.img missing — no rootfs image emitted."
        warn "Run images/mkrootfs.sh first (populates build/out/rootfs and build/out/system.img)."
        return 0
    fi

    command -v mke2fs >/dev/null 2>&1 || {
        warn "mke2fs not found — cannot bake rootfs image from staging."
        return 0
    }

    size_m="$(du -sm "${ROOTFS_STAGING}" | awk '{print $1}')"
    img_m=$(( size_m + size_m / 4 + 64 ))
    [ "${img_m}" -lt 512 ] && img_m=512
    log "Baking ext4 rootfs image (${img_m} MB) from staging ${ROOTFS_STAGING} ..."
    rm -f "${rootfs_img}"
    if command -v fakeroot >/dev/null 2>&1; then
        # fakeroot makes the baked image owned by root:root without needing
        # privileges; the staging tree itself is left untouched.
        fakeroot sh -c '
            chown -R 0:0 "$1"
            exec mke2fs -q -t ext4 -L nuxel-ocean -d "$1" "$2" "${3}M"
        ' _ "${ROOTFS_STAGING}" "${rootfs_img}" "${img_m}"
    else
        mke2fs -q -t ext4 -L nuxel-ocean -d "${ROOTFS_STAGING}" "${rootfs_img}" "${img_m}M"
    fi
    e2fsck -fy "${rootfs_img}" >/dev/null 2>&1 || true
    resize2fs -M "${rootfs_img}" >/dev/null 2>&1 || true
    log "Rootfs image: ${rootfs_img} (ext4, writable, NO dm-verity/AVB — Phase 1)"
}
_bake_rootfs_image

# --- 6. lk2nd bootloader image (promised artifact) --------------------------
# lk2nd (msm8916-mainline/lk2nd, msm8953 target) is required on this device:
# the stock ABOOT cannot accept mainline DTBs/cmdline, so lk2nd is flashed to
# the boot partition first (dtbo MUST already be in place — enforced by
# boot/g7power/flash.sh) and provides the fastboot that flashes the Nuxel
# boot image. If it is not built yet the artifact set is INCOMPLETE.
LK2ND_IMG="${LK2ND_BUILD_DIR}/lk2nd.img"
LK2ND_MISSING=0
if [ -f "${LK2ND_IMG}" ]; then
    cp -a "${LK2ND_IMG}" "${BOOT_OUT}/lk2nd.img"
    log "lk2nd.img: copied from ${LK2ND_IMG}"
else
    warn "lk2nd.img: NOT YET BUILT"
    warn "Build the msm8953 lk2nd target per boot/g7power/lk2nd/README.md,"
    warn "then re-run this build for the full artifact set."
    LK2ND_MISSING=1
fi

# --- 7. Build manifest ------------------------------------------------------
KERNEL_COMMIT="unknown"
if [ -d "${KSRC}/.git" ]; then
    KERNEL_COMMIT="$(git -C "${KSRC}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
fi
cat > "${BOOT_OUT}/build-manifest.json" <<JSON
{
  "device_key": "g7power",
  "codename": "ocean",
  "soc": "sdm632",
  "kernel_commit": "${KERNEL_COMMIT}",
  "kernel_source": "linux-postmarketos-qcom-msm8953",
  "dtb": "$(basename "${DTB}")",
  "boot_image_format": "android-boot-header-v1",
  "page_size": 2048,
  "dm_verity": false,
  "avb": false,
  "phase": 1,
  "build_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "notes": "Phase 1 bring-up image: rootfs writable, no dm-verity/AVB; A-only eMMC (boot/system/vendor/dtbo/userdata/recovery); boot chain PBL -> stock ABOOT -> lk2nd -> mainline Linux -> initramfs -> rootfs; modem/camera/sensors deferred; load addresses from docs/g7power-device-inventory.md (Phase 0)."
}
JSON
log "Build manifest: ${BOOT_OUT}/build-manifest.json"

log "Done. Artifacts under ${BOOT_OUT}:"
ls -lh "${BOOT_OUT}" | sed 's/^/  /'
if [ "${LK2ND_MISSING}" -eq 1 ]; then
    warn "MISSING ARTIFACT: lk2nd.img — the output above is INCOMPLETE."
    warn "lk2nd.img: NOT YET BUILT — build the msm8953 target per boot/g7power/lk2nd/README.md"
    warn "Then re-run this build for the full artifact set."
fi
