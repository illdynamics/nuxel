#!/usr/bin/env bash
# =============================================================================
# Nuxel S10+ Rootfs/Boot Build Orchestration — Samsung Galaxy S10+ (beyond2lte)
#
# Assembles the S10+ boot images and rootfs image under build/out/s10plus/:
#   * u-boot-beyond2lte.img       (U-Boot wrapped as a v1 boot.img)
#   * nuxel-beyond2lte-boot.img   (Nuxel kernel + initramfs as a v1 boot.img)
#   * nuxel-beyond2lte-rootfs.img (ext4 rootfs for the userdata partition)
#   * build-manifest.json         (device key, kernel commit, build timestamp)
#
# Usage:
#   NUXEL_DEVICE=s10plus bash images/s10plus/build.sh [--device s10plus] [--help] [--no-uboot]
#
# Inputs required (abort with a clear message when missing):
#   * kernel/s10plus/.build/out/arch/arm64/boot/Image.gz   (kernel/s10plus/build-kernel.sh)
#   * a beyond2lte DTB under kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/
#   * a shared initramfs: first existing of boot/initramfs/, boot/boot.img/,
#     build/boot-artifact/ (see --help for the search order)
#   * kernel/s10plus/.build/u-boot/u-boot.bin               (boot/s10plus/uboot-chainload.sh)
#
# Phase 1 emits NO dm-verity/AVB-signed image on purpose: the rootfs must stay
# writable during bring-up (U-Boot chainload + kernel + userspace are not yet
# stable enough for a verified-boot chain). dm-verity/AVB is a later phase.
#
# This script is device-isolated: it only ever writes under build/out/s10plus/
# and never touches any other device's output tree, and it never flashes
# anything to a device (see boot/s10plus/flash.sh).
# The S10+ (Exynos) has no Android-bootloader-mode flashing — flashing is
# TWRP (adb+dd) or Download Mode (Odin/heimdall) only; this script only
# builds artifacts and never flashes a device.
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

log()  { echo "[nuxel-s10plus-build] $*"; }
warn() { echo "[nuxel-s10plus-build][warn] $*" >&2; }
err()  { echo "[nuxel-s10plus-build][error] $*" >&2; }

usage() {
    cat <<'EOF'
Usage: NUXEL_DEVICE=s10plus bash images/s10plus/build.sh [--device s10plus] [--help] [--no-uboot]

Builds the S10+ (beyond2lte, Exynos 9820) boot + rootfs artifacts into
build/out/s10plus/:

  u-boot-beyond2lte.img       U-Boot (chiffathefox/u-boot exynos9820) wrapped
                              as a legacy Android boot image header v1
  nuxel-beyond2lte-boot.img   linux-postmarketos-exynos9820 Image.gz +
                              initramfs + exynos9820-beyond2lte.dtb as a v1
                              boot image
  nuxel-beyond2lte-rootfs.img ext4 rootfs image (for the userdata partition)
  build-manifest.json         device key, kernel commit, build timestamp

Required inputs (abort if missing):
  kernel/s10plus/.build/out/arch/arm64/boot/Image.gz   (build-kernel.sh)
  a beyond2lte DTB under kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/
  shared initramfs (first existing of):
    boot/initramfs/initramfs.cpio.gz                   (spec path)
    boot/boot.img/initramfs.cpio.gz                    (images/build.sh output)
    build/boot-artifact/initramfs.cpio.gz              (Makefile consolidation)
  kernel/s10plus/.build/u-boot/u-boot.bin              (uboot-chainload.sh;
                                                        skip with --no-uboot)

Phase 1 emits NO dm-verity/AVB image: the rootfs stays writable during
bring-up. Phase 0 device inventory (docs/s10plus-device-inventory.md) must be
filled before a real build; --help is exempt.

Options:
  --no-uboot    skip u-boot-beyond2lte.img when u-boot.bin is absent; the
                final summary marks the artifact set INCOMPLETE.

This script is device-isolated: it only ever writes under build/out/s10plus/
and never touches any other device's build output.
EOF
}

# --help exits before any gate work (device selection + inventory gate).
# --no-uboot is parsed here too; it only skips the U-Boot boot image.
NO_UBOOT=0
for arg in "$@"; do
    case "$arg" in
        --help|-h) usage; exit 0 ;;
        --no-uboot) NO_UBOOT=1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Device guard — S10+ only. Explicit selection required (env or --device);
# the shared selector never silently guesses. After this guard,
# ${NUXEL_DEVICE_DIR} is "s10plus" and every per-device path below is
# derived from it, so no other device's tree can be touched.
# ---------------------------------------------------------------------------
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || {
    err "images/s10plus/build.sh is ONLY for s10plus. Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

# Per-device tree (selector-verified: == s10plus).
DEVICE_DIR="${NUXEL_DEVICE_DIR}"
KERNEL_OUT="${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/out"
KSRC="${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/src"
UBOOT_BUILD_DIR="${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/u-boot"
BOOT_OUT="${NUXEL_ROOT}/build/out/${DEVICE_DIR}"
ROOTFS_STAGING="${NUXEL_ROOT}/build/out/rootfs"   # images/mkrootfs.sh staging dir
PACKER="${NUXEL_ROOT}/boot/${DEVICE_DIR}/pack-boot-v1.sh"

# ---------------------------------------------------------------------------
# Inventory gate (Phase 0) — see docs/s10plus-device-inventory.md
# Blocks real build operations until the operator has filled the critical
# fields from the physical device. Never blocks --help (handled above).
# ---------------------------------------------------------------------------
_check_s10plus_inventory() {
    local inventory="${NUXEL_ROOT}/docs/s10plus-device-inventory.md"
    # Fail closed: the inventory document must exist (Phase 0), otherwise the
    # grep below would pass vacuously on a missing/unreadable file and let
    # PLACEHOLDER load addresses / UNKNOWN firmware filenames through.
    if [ ! -f "${inventory}" ]; then
        err "docs/s10plus-device-inventory.md missing — run Phase 0 collection"
        err "Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAME"
        exit 1
    fi
    # Check if UNKNOWN placeholders are still present in critical fields
    if grep -qE "KERNEL_ADDR:.*PLACEHOLDER|RAMDISK_ADDR:.*PLACEHOLDER|TAGS_ADDR:.*PLACEHOLDER|WIFI_FW_FILENAME:.*UNKNOWN" "${inventory}"; then
        echo "ERROR: S10+ device inventory is incomplete."
        echo "       Run Phase 0 collection commands in docs/s10plus-device-inventory.md"
        echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAME"
        echo "       Then re-run this script."
        exit 1
    fi
}
_check_s10plus_inventory

# --- 1. Required inputs ----------------------------------------------------
KERNEL_IMG="${KERNEL_OUT}/arch/arm64/boot/Image.gz"
[ -f "${KERNEL_IMG}" ] || {
    err "Kernel image not found: ${KERNEL_IMG}"
    err "Run: NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone"
    exit 1
}

# --- build the board DTB (SoC base + board-revision overlay) ----------------
# The downstream Samsung Exynos 9820 tree ships ONLY the SoC base DTB
# (dts/exynos/exynos9820.dtb) plus per-board-revision overlays
# (dts/samsung/exynos9820-beyond2lte_eur_open_<rev>.dtbo). S-Boot normally
# applies the overlay from the DTBO partition at boot; for a self-contained
# boot.img we merge base + overlay into a single exynos9820-beyond2lte.dtb with
# fdtoverlay (device-tree-compiler). Highest available board revision is used;
# the device's S-Boot still applies its own matching DTBO at runtime.
DTB_BASE="${KERNEL_OUT}/arch/arm64/boot/dts/exynos/exynos9820.dtb"
DTB_SAMSUNG_DIR="${KERNEL_OUT}/arch/arm64/boot/dts/samsung"
DTB_MERGED="${DTB_SAMSUNG_DIR}/exynos9820-beyond2lte.dtb"
if [ ! -s "${DTB_MERGED}" ] && [ -s "${DTB_BASE}" ]; then
    _overlay="$(find "${DTB_SAMSUNG_DIR}" -maxdepth 1 \
        -name 'exynos9820-beyond2lte_eur_open_*.dtbo' 2>/dev/null | sort -V | tail -1 || true)"
    if [ -n "${_overlay}" ] && command -v fdtoverlay >/dev/null 2>&1; then
        log "Merging board DTB: exynos9820.dtb + $(basename "${_overlay}") -> exynos9820-beyond2lte.dtb"
        if ! fdtoverlay -i "${DTB_BASE}" -o "${DTB_MERGED}" "${_overlay}"; then
            err "fdtoverlay failed to merge ${_overlay} onto ${DTB_BASE}"
            exit 1
        fi
    else
        warn "Cannot build merged board DTB (overlay='${_overlay}' fdtoverlay=$(command -v fdtoverlay || echo missing))"
    fi
fi

# Board DTB search. Prefer the merged standalone DTB (exynos9820-beyond2lte.dtb)
# under dts/samsung/, then any exynos9820-beyond2lte*.dtb, then a mainline-style
# dts/exynos/ board DTB. find(1) is used so the search is quiet and
# deterministic even when no DTB exists yet.
DTB="$(find "${DTB_SAMSUNG_DIR}" -maxdepth 1 \
    -name 'exynos9820-beyond2lte.dtb' 2>/dev/null | head -1 || true)"
if [ -z "${DTB}" ]; then
    DTB="$(find "${DTB_SAMSUNG_DIR}" -maxdepth 1 \
        -name 'exynos9820-beyond2lte*.dtb' 2>/dev/null | sort -V | tail -1 || true)"
fi
if [ -z "${DTB}" ]; then
    DTB="$(find "${KERNEL_OUT}/arch/arm64/boot/dts/exynos" -maxdepth 1 \
        -name '*beyond2lte*.dtb' 2>/dev/null | sort -V | tail -1 || true)"
fi
[ -n "${DTB}" ] || {
    err "No beyond2lte DTB found under ${KERNEL_OUT}/arch/arm64/boot/dts/{samsung,exynos}/"
    err "Run: NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone"
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
log "Building S10+ artifacts into ${BOOT_OUT}"

# --- 1b. Phase-0 inventory load addresses ------------------------------------
# The gate above guarantees KERNEL_ADDR/RAMDISK_ADDR/TAGS_ADDR are filled, so
# feed the inventoried (device-derived) values to the packer — otherwise every
# post-inventory build would silently use the packer's PLACEHOLDER defaults.
INVENTORY="${NUXEL_ROOT}/docs/s10plus-device-inventory.md"
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

# --- 2. Boot images via boot/s10plus/pack-boot-v1.sh ------------------------
# Legacy Android boot image header v1 (page 2048, ANDROID! magic) — the format
# S-Boot reads. Load addresses are PLACEHOLDERs until Phase 0 inventory; the
# packer prints a warning and supports --addresses-from-device for real values.
CMDLINE="buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw"

log "Packing Nuxel boot image (kernel + initramfs + DTB, v1 header)..."
python3 "${PACKER}" \
    --kernel "${KERNEL_IMG}" \
    --ramdisk "${INITRAMFS}" \
    --dtb "${DTB}" \
    --cmdline "${CMDLINE}" \
    "${PACK_ADDR_ARGS[@]}" \
    --output "${BOOT_OUT}/nuxel-beyond2lte-boot.img"

# u-boot-beyond2lte.img is a promised artifact, so u-boot.bin is a required
# input for a real build: abort (pointing at the U-Boot chainload builder)
# unless the operator explicitly opts out with --no-uboot.
UBOOT_BIN="${UBOOT_BUILD_DIR}/u-boot.bin"
if [ "${NO_UBOOT}" -eq 1 ]; then
    warn "--no-uboot: skipping u-boot-beyond2lte.img — output will be INCOMPLETE."
    warn "Build U-Boot with: NUXEL_DEVICE=s10plus bash boot/s10plus/uboot-chainload.sh"
elif [ -f "${UBOOT_BIN}" ]; then
    log "Packing U-Boot boot image (u-boot.bin as v1 kernel slot)..."
    python3 "${PACKER}" \
        --kernel "${UBOOT_BIN}" \
        --ramdisk /dev/null \
        --cmdline "" \
        "${PACK_ADDR_ARGS[@]}" \
        --output "${BOOT_OUT}/u-boot-beyond2lte.img"
else
    warn "U-Boot binary not found: ${UBOOT_BIN}"
    warn "Skipping u-boot-beyond2lte.img (the proven downstream/heimdall flash"
    warn "path does NOT need U-Boot; it flashes nuxel-beyond2lte-boot.img to BOOT"
    warn "and the rootfs to SYSTEM). Build U-Boot only for the mainline stretch"
    warn "path: NUXEL_DEVICE=s10plus bash boot/s10plus/uboot-chainload.sh"
fi

# --- 3. Userspace rootfs via the device-agnostic builder --------------------
# images/mkrootfs.sh is the shared, device-agnostic userspace builder
# (Flatpak runtime + Nuxel services/apps/security configs). It is invoked
# as-is and populates build/out/rootfs (and, when its bake step runs,
# build/out/system.img). OpenRC is the phone-target init (pmOS-style).
log "Assembling Nuxel userspace with images/mkrootfs.sh (device-agnostic)..."
export NUXEL_INIT="${NUXEL_INIT:-openrc}"
bash "${NUXEL_ROOT}/images/mkrootfs.sh"

# --- 4. Overlay device-specific content into the rootfs staging ------------
# All S10+ content is installed AFTER the shared userspace build so nothing
# device-specific ever leaks into the shared pipeline.

if [ -d "${NUXEL_ROOT}/firmware/${DEVICE_DIR}/blobs" ]; then
    log "Installing S10+ firmware blobs into rootfs staging..."
    # --install honors the manifest's required/pending logic; --force-pending
    # lets already-pulled blobs land while UNKNOWN-checksum entries are only
    # reported (never fatal) during bring-up. The script self-guards on
    # NUXEL_DEVICE_KEY==s10plus and aborts before Phase 0 inventory is filled,
    # so failures here are expected pre-inventory and are non-fatal for the
    # boot images (the rootfs just ships without firmware until then).
    NUXEL_DEVICE=s10plus bash "${NUXEL_ROOT}/firmware/${DEVICE_DIR}/install-firmware.sh" \
        --install --force-pending --rootfs-staging "${ROOTFS_STAGING}" || \
        warn "firmware install reported pending/missing blobs (expected pre-Phase-0)."
else
    warn "firmware/${DEVICE_DIR}/blobs not present — run --twrp-pull on the S10+ first."
fi

if [ -d "${NUXEL_ROOT}/configs/${DEVICE_DIR}" ]; then
    log "Installing S10+ device configs into rootfs staging..."
    mkdir -p "${ROOTFS_STAGING}/etc/nuxel/device/${DEVICE_DIR}"
    cp -a "${NUXEL_ROOT}/configs/${DEVICE_DIR}/." "${ROOTFS_STAGING}/etc/nuxel/device/${DEVICE_DIR}/"
    if [ -f "${NUXEL_ROOT}/device/${DEVICE_DIR}/90-nuxel-beyond2lte.rules" ]; then
        mkdir -p "${ROOTFS_STAGING}/etc/udev/rules.d"
        cp -a "${NUXEL_ROOT}/device/${DEVICE_DIR}/90-nuxel-beyond2lte.rules" \
            "${ROOTFS_STAGING}/etc/udev/rules.d/"
    fi
    if [ -f "${NUXEL_ROOT}/device/${DEVICE_DIR}/nuxel-beyond2lte.conf" ]; then
        mkdir -p "${ROOTFS_STAGING}/etc/nuxel"
        cp -a "${NUXEL_ROOT}/device/${DEVICE_DIR}/nuxel-beyond2lte.conf" \
            "${ROOTFS_STAGING}/etc/nuxel/"
    fi
else
    warn "configs/${DEVICE_DIR} not present — S10+ display/audio/touch configs skipped."
fi

# Kernel modules: primary location per the spec is
# kernel/s10plus/.build/out/lib/modules (INSTALL_MOD_PATH=<KOUT>); also accept
# a .build/modules staging used by some module-install workflows.
KERNEL_MODULES_DIR=""
if [ -d "${KERNEL_OUT}/lib/modules" ]; then
    KERNEL_MODULES_DIR="${KERNEL_OUT}/lib/modules"
elif [ -d "${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/modules/lib/modules" ]; then
    KERNEL_MODULES_DIR="${NUXEL_ROOT}/kernel/${DEVICE_DIR}/.build/modules/lib/modules"
fi
if [ -n "${KERNEL_MODULES_DIR}" ]; then
    log "Installing S10+ kernel modules into rootfs staging (/lib/modules)..."
    mkdir -p "${ROOTFS_STAGING}/lib/modules"
    cp -a "${KERNEL_MODULES_DIR}/." "${ROOTFS_STAGING}/lib/modules/"
else
    warn "No kernel modules found (checked ${KERNEL_OUT}/lib/modules). Skipped."
    warn "Produce them with:"
    warn "  make -C \"${KSRC}\" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \\"
    warn "       O=\"${KERNEL_OUT}\" modules_install INSTALL_MOD_PATH=\"${KERNEL_OUT}\""
fi

# --- 5. Emit rootfs image ---------------------------------------------------
# Phase 1: plain ext4, writable. NO dm-verity/AVB yet — the bring-up rootfs
# must stay writable (U-Boot chainload + kernel + userspace are not stable
# enough for a verified-boot chain); dm-verity/AVB is deferred to a later
# phase. The image is baked from the final staging dir so the S10+ firmware,
# configs and kernel modules are included.
_bake_rootfs_image() {
    local rootfs_img="${BOOT_OUT}/nuxel-beyond2lte-rootfs.img"
    local size_m img_m

    if [ ! -d "${ROOTFS_STAGING}" ] || [ -z "$(ls -A "${ROOTFS_STAGING}" 2>/dev/null || true)" ]; then
        # Staging empty (mkrootfs produced nothing) — fall back to a
        # pre-baked shared system.img when one exists.
        if [ -f "${NUXEL_ROOT}/build/out/system.img" ]; then
            cp -a "${NUXEL_ROOT}/build/out/system.img" "${rootfs_img}"
            log "Rootfs image: ${rootfs_img} (copy of build/out/system.img; NO dm-verity Phase 1)"
            warn "build/out/system.img was baked before the S10+ overlays — re-run with a"
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
            exec mke2fs -q -t ext4 -L nuxel-beyond2lte -d "$1" "$2" "${3}M"
        ' _ "${ROOTFS_STAGING}" "${rootfs_img}" "${img_m}"
    else
        mke2fs -q -t ext4 -L nuxel-beyond2lte -d "${ROOTFS_STAGING}" "${rootfs_img}" "${img_m}M"
    fi
    e2fsck -fy "${rootfs_img}" >/dev/null 2>&1 || true
    resize2fs -M "${rootfs_img}" >/dev/null 2>&1 || true
    log "Rootfs image: ${rootfs_img} (ext4, writable, NO dm-verity/AVB — Phase 1)"
}
_bake_rootfs_image

# --- 6. Build manifest ------------------------------------------------------
KERNEL_COMMIT="unknown"
if [ -d "${KSRC}/.git" ]; then
    KERNEL_COMMIT="$(git -C "${KSRC}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
fi
cat > "${BOOT_OUT}/build-manifest.json" <<JSON
{
  "device_key": "s10plus",
  "codename": "beyond2lte",
  "soc": "exynos9820",
  "kernel_commit": "${KERNEL_COMMIT}",
  "kernel_source": "Linux4/android_kernel_samsung_exynos9820@f7194c1d (Linux 4.14.253 downstream)",
  "dtb": "$(basename "${DTB}")",
  "boot_image_format": "android-boot-header-v1",
  "page_size": 2048,
  "dm_verity": false,
  "avb": false,
  "phase": 1,
  "build_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "notes": "Phase 1 bring-up image: rootfs writable, no dm-verity/AVB, modem/camera/sensors deferred. Boot load addresses come from docs/s10plus-device-inventory.md (Phase 0); the board DTB is base exynos9820.dtb + highest-rev board DTBO merged with fdtoverlay."
}
JSON
log "Build manifest: ${BOOT_OUT}/build-manifest.json"

# --- 7. Per-artifact checksums (sha256sums.txt) -----------------------------
# Release consumers verify each flashed image before writing it to the device.
_sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi
}
( cd "${BOOT_OUT}"
  : > sha256sums.txt
  for f in nuxel-beyond2lte-boot.img nuxel-beyond2lte-rootfs.img u-boot-beyond2lte.img; do
      if [ -f "${f}" ]; then _sha256_of "${f}" >> sha256sums.txt; fi
  done
  : )
log "Checksums: ${BOOT_OUT}/sha256sums.txt"
cat "${BOOT_OUT}/sha256sums.txt" | sed 's/^/  /'

log "Done. Artifacts under ${BOOT_OUT}:"
ls -lh "${BOOT_OUT}" | sed 's/^/  /'
if [ ! -f "${BOOT_OUT}/u-boot-beyond2lte.img" ]; then
    warn "MISSING ARTIFACT: u-boot-beyond2lte.img — the output above is INCOMPLETE."
    warn "Build U-Boot with: NUXEL_DEVICE=s10plus bash boot/s10plus/uboot-chainload.sh"
    warn "Then re-run this build (without --no-uboot) for the full artifact set."
fi
