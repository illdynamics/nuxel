#!/bin/bash
set -euo pipefail

# Nuxel Flash Script for Google Pixel 10 Pro XL (mustang) — Immutable OS
#
# Flashes dm-verity enabled system images. Supports development mode
# (AVB disabled) and production mode (user-signed, relocked bootloader).
#
# Device: Pixel 10 Pro XL (codename: mustang)
# Serial: 58211FDCQ001LA
# HW: MP1.0, SKU G45RY

# Resolve the repo root whether this script is invoked directly or through
# the legacy symlink boot/flash.sh -> google-pixel-10-pro-xl/flash.sh.
_NUXEL_SRC="${BASH_SOURCE[0]}"
while [ -h "${_NUXEL_SRC}" ]; do
    _NUXEL_DIR="$(cd -P "$(dirname "${_NUXEL_SRC}")" && pwd)"
    _NUXEL_SRC="$(readlink "${_NUXEL_SRC}")"
    case "${_NUXEL_SRC}" in
        /*) ;;
        *) _NUXEL_SRC="${_NUXEL_DIR}/${_NUXEL_SRC}" ;;
    esac
done
NUXXEL_ROOT="$(cd -P "$(dirname "${_NUXEL_SRC}")/../.." && pwd)"
BOOT_DIR="${NUXXEL_ROOT}/boot"
BUILD_OUT="${NUXXEL_ROOT}/build/out"
FLASH_DIR="${BUILD_OUT}/flashable"

# --- boot-artifact packaging (briq-a1): consume kernel/${NUXEL_DEVICE_DIR}/.build/out + initramfs
# The genuine boot artifact chain is produced by images/build.sh and lands in
# boot/boot.img/ (boot.img + initramfs.cpio.gz + unpacked Image.gz/dtbs).
BOOT_ARTIFACT_DIR="${NUXXEL_ROOT}/boot/boot.img"
# Device selection: this per-device script is mustang-only. The shared
# selector never silently guesses; the wrapper defaults to mustang only for
# backward compatibility (this script historically WAS the mustang flash tool).
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
KERNEL_OUT="${NUXXEL_KERNEL_OUT:-${NUXXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/out}"


# Default image paths
BOOT_IMG="${BOOT_ARTIFACT_DIR}/boot.img"
BOOT_INITRAMFS="${BOOT_ARTIFACT_DIR}/initramfs.cpio.gz"
[ -f "${BOOT_IMG}" ] || BOOT_IMG="${FLASH_DIR}/boot.img"
INIT_BOOT_IMG="${FLASH_DIR}/init_boot.img"
VENDOR_BOOT_IMG="${FLASH_DIR}/vendor_boot.img"
DTBO_IMG="${FLASH_DIR}/dtbo.img"
VBMETA_IMG="${FLASH_DIR}/vbmeta.img"
SYSTEM_IMG="${FLASH_DIR}/system.img"
MODEM_IMG="${FLASH_DIR}/modem.img"

# Options
TARGET_SLOT=""
DO_UNLOCK=0
DO_RELOCK=0
DO_RELOCK_CUSTOM=0
DO_WIPE=0
FORCE=0
DO_BUILD_BOOT=0
DO_PUBLISH_BOOT=0
NO_REBOOT=0
SKIP_AVB=0
ALLOW_UNVERITY_DEV=0
PRODUCTION=0

# Custom-key relock path (user-generated AVB RSA key + locksigned vbmeta)
RELOCK_CUSTOM_KEY=""
RELOCK_AVBTOOL="${RELOCK_AVBTOOL:-./external/avbtool/avbtool}"

# ANSI colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

[ "${NUXEL_DEVICE_KEY}" = "mustang" ] || {
    log_error "boot/${NUXEL_DEVICE_DIR}/flash.sh is ONLY for mustang. Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

usage() {
    cat <<EOF
Nuxel Flash Tool — Google Pixel 10 Pro XL (mustang)

Device key: ${NUXEL_DEVICE_KEY}  (device dir: ${NUXEL_DEVICE_DIR})

Usage: $0 [options]
  --boot <img>              override boot.img path
  --boot-artifact-dir <dir> override boot artifact dir (boot/boot.img)
  --kernel-out <dir>        override kernel build output dir
  --build-boot              run images/build.sh first to refresh artifacts
  --publish-boot            publish boot artifacts into build/out/flashable
  --vendor-boot <img>       override vendor_boot.img path
  --init-boot <img>         override init_boot.img path
  --dtbo <img>              override dtbo.img path
  --vbmeta <img>            override vbmeta.img path
  --modem <img>             override modem.img path
  --system <img>            override system.img path
  --slot <a|b>              target slot (default: current active)
  --unlock                  unlock the bootloader (fastboot flashing unlock)
  --relock                  relock the bootloader with a signed vbmeta
  --relock-custom-key <pem> relock using a user AVB key (signs vbmeta first)
  --production              production mode (no interactive prompts)
  --wipe                    wipe userdata after flashing
  --force                   skip device identity confirmation
  --no-reboot               do not reboot after flashing
  --skip-avb                skip AVB verification
  --allow-unverity-dev      allow dm-verity disabled dev images
  --device <key>            device key (must be mustang; accepted for
                            consistency with the shared device selector)
  --help|-h                 this message

NOTE: this tool is for the Google Pixel 10 Pro XL (mustang) ONLY. The
Samsung Galaxy S10+ (Exynos) has NO fastboot and must never be flashed
with this script (see boot/s10plus/flash.sh).
EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --device) shift 2 ;;
        --help|-h) usage ;;
        --boot) BOOT_IMG="$2"; shift 2 ;;
        --boot-artifact-dir) BOOT_ARTIFACT_DIR="$2"; shift 2 ;;
        --kernel-out) KERNEL_OUT="$2"; shift 2 ;;
        --build-boot) DO_BUILD_BOOT=1; shift ;;
        --publish-boot) DO_PUBLISH_BOOT=1; shift ;;
        --vendor-boot) VENDOR_BOOT_IMG="$2"; shift 2 ;;
        --init-boot) INIT_BOOT_IMG="$2"; shift 2 ;;
        --dtbo) DTBO_IMG="$2"; shift 2 ;;
        --vbmeta) VBMETA_IMG="$2"; shift 2 ;;
        --modem) MODEM_IMG="$2"; shift 2 ;;
        --system) SYSTEM_IMG="$2"; shift 2 ;;
        --slot) TARGET_SLOT="$2"; shift 2 ;;
        --unlock) DO_UNLOCK=1; shift ;;
        --relock) DO_RELOCK=1; shift ;;
        --relock-custom-key) DO_RELOCK_CUSTOM=1; RELOCK_CUSTOM_KEY="$2"; shift 2 ;;
        --production) PRODUCTION=1; shift ;;
        --wipe) DO_WIPE=1; shift ;;
        --force) FORCE=1; shift ;;
        --no-reboot) NO_REBOOT=1; shift ;;
        --skip-avb) SKIP_AVB=1; shift ;;
        --allow-unverity-dev) ALLOW_UNVERITY_DEV=1; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

check_fastboot() {
    if ! command -v fastboot &>/dev/null; then
        log_error "fastboot not found. Install android-tools-fastboot."
        exit 1
    fi
    log_ok "fastboot available ($(fastboot --version | head -1))"
}

check_device() {
    local devices
    devices="$(fastboot devices 2>/dev/null)"
    if [ -z "${devices}" ]; then
        log_error "No device in fastboot mode detected."
        echo "Boot into fastboot: Volume Down + Power, then connect USB."
        exit 1
    fi
    
    local serial
    serial="$(echo "${devices}" | head -1 | awk '{print $1}')"
    log_info "Device: ${serial}"
    
    # Verify mustang
    local product
    product="$(fastboot getvar product 2>&1 | grep -o 'mustang[^ ]*' || echo "unknown")"
    if [ "${product}" != "mustang" ] && [ "${FORCE}" -eq 0 ]; then
        log_warn "Expected mustang, got ${product}. Continue? [y/N]"
        read -r ans; [ "${ans}" != "y" ] && [ "${ans}" != "Y" ] && exit 1
    fi
    log_ok "Device: Google Pixel 10 Pro XL (mustang) — ${serial}"
}

unlock_bootloader() {
    local unlocked
    unlocked="$(fastboot getvar unlocked 2>&1 || true)"
    if echo "${unlocked}" | grep -q "yes"; then
        log_ok "Bootloader already unlocked"
        return 0
    fi
    
    log_warn "=========================================="
    log_warn "BOOTLOADER UNLOCK — Factory resets device!"
    log_warn "=========================================="
    echo -n "Proceed? [y/N] "
    read -r ans; [ "${ans}" != "y" ] && [ "${ans}" != "Y" ] && exit 1
    
    fastboot flashing unlock
    echo "Confirm on device screen. Press Enter after..."
    read -r
    
    # Wait for reconnection
    sleep 5
    if ! fastboot devices 2>/dev/null | grep -q .; then
        log_info "Device may have rebooted. Re-enter fastboot and press Enter..."
        read -r
        check_device
    fi
    log_ok "Bootloader unlocked"
}

relock_bootloader() {
    log_warn "=========================================="
    log_warn "BOOTLOADER RELOCK — Production mode"
    log_warn "=========================================="
    echo ""
    log_warn "This requires signed images with your AVB key."
    log_warn "If the bootloader is relocked with corrupted images,"
    log_warn "the device WILL NOT BOOT until you flash signed images."
    echo ""
    log_info "Before relocking, ensure:"
    log_info "  1. boot.img is signed with your AVB key"
    log_info "  2. system.img has dm-verity hash tree"
    log_info "  3. vbmeta.img chains boot + system verification"
    log_info "  4. Your public key is enrolled: fastboot oem avb_set_key <key>"
    echo ""
    
    if [ "${PRODUCTION}" -ne 1 ]; then
        echo -n "Enroll AVB key and relock? [y/N] "
        read -r ans; [ "${ans}" != "y" ] && [ "${ans}" != "Y" ] && return 0
    fi
    
    # Enroll AVB public key
    local avb_key="${NUXXEL_ROOT}/keys/nuxel-avb-public.bin"
    if [ -f "$avb_key" ]; then
        log_info "Enrolling AVB public key..."
        fastboot oem avb_set_key "$avb_key"
        log_ok "AVB key enrolled"
    else
        log_warn "AVB public key not found at ${avb_key}"
        log_warn "You must enroll a key before relocking."
        echo -n "Skip key enrollment and relock anyway? [y/N] "
        read -r ans; [ "${ans}" != "y" ] && [ "${ans}" != "Y" ] && return 0
    fi
    
    log_info "Relocking bootloader..."
    fastboot flashing lock
    echo "Confirm on device screen. Press Enter after..."
    read -r
    
    log_ok "Bootloader relocked. Device will only boot Nuxel-signed images."
}

# ---------------------------------------------------------------------------
# relock_with_custom_key — production relock path using the Nuxel user key
#
# This signs vbmeta.img with the user's RSA2048 key (through
# images/google-pixel-10-pro-xl/avb/sign.sh
# and avbtool) then sets the vbmeta rollback flag state=locksigned before
# running `fastboot oem lock`. Used from:
#
#   boot/flash.sh --relock-custom-key keys/nuxel-avb-private.pem
#
# The key must be the SAME one whose public key is enrolled in the bootloader
# (fastboot oem avb_set_key <pub>). Signing and enrolling must match or the
# device will not boot after relock.
# ---------------------------------------------------------------------------
relock_with_custom_key() {
    local key="${RELOCK_CUSTOM_KEY}"
    if [ -z "$key" ]; then
        # Fall back to the default key path.
        key="${NUXXEL_ROOT}/keys/nuxel-avb-private.pem"
    fi
    if [ ! -f "$key" ]; then
        log_error "Custom AVB key not found: ${key}"
        log_error "Generate one first (see images/${NUXEL_DEVICE_DIR}/avb/mustang-avb.conf), e.g.:"
        log_error "  openssl genrsa -out keys/nuxel-avb-private.pem 2048"
        exit 1
    fi

    log_warn "=========================================="
    log_warn "CUSTOM-KEY RELOCK — Production mode"
    log_warn "Device signature = locksigned"
    log_warn "=========================================="
    echo ""
    log_info "Key:      ${key}"
    log_info "avbtool:  ${RELOCK_AVBTOOL}"
    echo ""

    # 1. Sign the boot chain (boot/dtbo/system/vendor -> vbmeta.img) with this key.
    log_info "Signing boot chain with avbtool..."
    if [ -x "${RELOCK_AVBTOOL}" ] || command -v "${RELOCK_AVBTOOL}" &>/dev/null; then
        bash "${NUXXEL_ROOT}/images/${NUXEL_DEVICE_DIR}/avb/sign.sh"             --key "$key"             --avbtool "${RELOCK_AVBTOOL}" --algorithm SHA256_RSA2048 || {
            log_error "AVB signing failed. Aborting relock."
            exit 1
        }
        log_ok "Boot chain signed."
    else
        log_warn "avbtool not found (${RELOCK_AVBTOOL}); assuming images are already signed."
    fi

    local vbmeta="${FLASH_DIR}/vbmeta.img"
    [ -f "$vbmeta" ] || vbmeta="${BUILD_OUT}/vbmeta.img"
    if [ ! -f "$vbmeta" ]; then
        log_error "Signed vbmeta.img not found at ${vbmeta}"
        log_error "Run images/${NUXEL_DEVICE_DIR}/avb/sign.sh first."
        exit 1
    fi

    # 2. Enroll the custom key's public half so the bootloader trusts it.
    local pubkey="${key%.pem}-public.bin"
    if [ -f "$pubkey" ]; then
        log_info "Enrolling AVB public key ${pubkey}..."
        fastboot oem avb_set_key "$pubkey"
        log_ok "Custom AVB key enrolled."
    else
        log_error "Public key not found: ${pubkey}. Extract it:"
        log_error "  ${RELOCK_AVBTOOL} extract_public_key --key $key --output ${pubkey}"
        exit 1
    fi

    # 3. Mark vbmeta as locksigned (state=locksigned) so the bootloader
    #    refuses to boot with unlocked state.
    log_info "Setting vbmeta state=locksigned..."
    fastboot oem avb_set_state locksigned || {
        log_warn "avb_set_state not supported; continuing (vbmeta already authoritative)."
    }

    # 4. Flash the signed vbmeta to both slots.
    #    The signed vbmeta produced by images/${NUXEL_DEVICE_DIR}/avb/sign.sh carries enforcement
    #    flags (verity + signature verification) cleared to 0, so the production
    #    relock must flash it with those flags intact.  Only an explicit
    #    --allow-unverity-dev (a pre-enrollment/unlock development context) may
    #    bypass verification.
    if [ "${ALLOW_UNVERITY_DEV}" -eq 1 ]; then
        log_warn "ALLOW_UNVERITY_DEV: flashing vbmeta with verity/verification disabled (DEV ONLY)"
        fastboot flash vbmeta_a --disable-verity --disable-verification "$vbmeta" || true
        fastboot flash vbmeta_b --disable-verity --disable-verification "$vbmeta" || true
    else
        log_info "Flashing signed vbmeta with enforcement flags intact..."
        fastboot flash vbmeta_a "$vbmeta" || true
        fastboot flash vbmeta_b "$vbmeta" || true
    fi

    # 5. Lock the bootloader.
    log_warn "Relocking bootloader..."
    fastboot flashing lock
    echo "Confirm on device screen. Press Enter after..."
    read -r

    log_ok "Bootloader relocked with custom key (state=locksigned)."
    log_ok "Device will only boot images signed by this key."
}

select_slot() {
    if [ -n "${TARGET_SLOT}" ]; then return; fi
    local current
    current="$(fastboot getvar current-slot 2>&1 | grep -o '[ab]' | head -1)"
    if [ "${current}" = "a" ]; then TARGET_SLOT="b"; else TARGET_SLOT="a"; fi
    log_info "Current slot: ${current}, Target: ${TARGET_SLOT}"
}

verify_image() {
    local path="$1" name="$2" min="${3:-1024}"
    
    if [ ! -f "$path" ]; then
        log_error "${name} NOT FOUND at ${path}"
        log_error "Cannot flash without ${name}. Run 'images/build.sh' first."
        log_error "Nuxel v0.4.0-alpha does NOT produce real flashable images yet."
        log_error "This flash script is for development/testing only."
        exit 3
    fi
    
    local size
    size=$(stat -f%z "$path" 2>/dev/null || stat -c%s "$path" 2>/dev/null || echo 0)
    
    if [ "${size}" -lt "${min}" ]; then
        log_error "${name} too small: ${size} bytes (minimum ${min})"
        exit 4
    fi
    
    # Check if file is entirely zero-filled (dev stub, not real image)
    if [ "${size}" -gt 0 ] && [ "${size}" -lt 104857600 ]; then
        local null_bytes
        null_bytes=$(head -c 4096 "$path" | tr -dc '\x00' | wc -c | tr -d ' ')
        if [ "${null_bytes}" -eq 4096 ]; then
            log_error "${name} is entirely zero-filled — DEV STUB, NOT FLASHABLE"
            log_error "Real images must be built from kernel + device tree + rootfs."
            log_error "See docs/build-guide.md for the full build pipeline."
            exit 5
        fi
    fi
    
    log_ok "${name} ($(numfmt --to=iec $size 2>/dev/null || echo "${size} bytes"))"
    return 0
}

flash_image() {
    local partition="$1" image="$2"
    local slot="${3:-${TARGET_SLOT}}"
    log_info "Flashing ${partition}_${slot}..."
    fastboot flash "${partition}_${slot}" "$image"
    log_ok "${partition}_${slot} flashed"
}

flash_vbmeta() {
    if [ "${SKIP_AVB}" -eq 1 ]; then return; fi
    if verify_image "${VBMETA_IMG}" "vbmeta.img" 1024; then
        if [ "${PRODUCTION}" -eq 1 ]; then
            flash_image vbmeta "${VBMETA_IMG}" a
            flash_image vbmeta "${VBMETA_IMG}" b
        else
            fastboot flash vbmeta_a --disable-verity --disable-verification "${VBMETA_IMG}"
            fastboot flash vbmeta_b --disable-verity --disable-verification "${VBMETA_IMG}"
        fi
        log_ok "vbmeta flashed"
    else
        # Generate minimal dev vbmeta
        local tmp
        tmp="$(mktemp)"
        python3 -c "
import struct
with open('${tmp}', 'wb') as f:
    f.write(b'AVB0')
    f.write(struct.pack('>II', 1, 65536))
    f.write(struct.pack('>I', 2))
    f.write(b'\x00' * 96)
    f.truncate(65536)
" 2>/dev/null || dd if=/dev/zero bs=64K count=1 of="$tmp" 2>/dev/null
        fastboot flash vbmeta_a --disable-verity --disable-verification "$tmp"
        fastboot flash vbmeta_b --disable-verity --disable-verification "$tmp"
        rm -f "$tmp"
        log_ok "Generated and flashed minimal vbmeta (development)"
    fi
}

flash_system_dmverity() {
    if [ ! -f "$SYSTEM_IMG" ]; then
        log_info "No system image at ${SYSTEM_IMG}, skipping"
        return
    fi
    
    # Enter fastbootd
    log_info "Entering fastbootd..."
    fastboot reboot fastboot
    sleep 3
    
    local retries=0
    while ! fastboot devices 2>/dev/null | grep -q .; do
        sleep 2; retries=$((retries + 1))
        [ "${retries}" -gt 15 ] && { log_error "Device not found in fastbootd"; exit 1; }
    done
    
    # Flash system with dm-verity
    log_info "Flashing system (dm-verity enabled)..."
    
    if [ -f "${SYSTEM_IMG}.verity" ]; then
        # Flash system + verity hash tree
        fastboot flash system "${SYSTEM_IMG}"
        fastboot flash verity "${SYSTEM_IMG}.verity"
        log_ok "System + dm-verity hash tree flashed"
    else
        fastboot flash system "${SYSTEM_IMG}"
        log_ok "System image flashed (no separate verity data)"
    fi
    
    # Return to bootloader
    fastboot reboot bootloader
    sleep 3
}


# =============================================================================
# boot artifact functions (briq-a1) — consume kernel/${NUXEL_DEVICE_DIR}/.build/out + initramfs
# =============================================================================

# ensure_boot_artifact(): run images/build.sh so boot/boot.img is fresh.
ensure_boot_artifact() {
    log_info "Building boot artifact chain (kernel -> boot.img + initramfs)..."
    if [ ! -f "${NUXXEL_ROOT}/images/build.sh" ]; then
        log_error "images/build.sh missing"
        exit 1
    fi
    bash "${NUXXEL_ROOT}/images/build.sh" --device "${NUXEL_DEVICE_KEY}" --skip-shadow 2>&1 || {
        log_error "images/build.sh failed"
        exit 1
    }
    # refresh defaults now that the artifact exists
    [ -f "${BOOT_ARTIFACT_DIR}/boot.img" ] && BOOT_IMG="${BOOT_ARTIFACT_DIR}/boot.img"
    [ -f "${BOOT_ARTIFACT_DIR}/initramfs.cpio.gz" ] && BOOT_INITRAMFS="${BOOT_ARTIFACT_DIR}/initramfs.cpio.gz"
}

# consume_kernel(): sanity-check that the kernel build output we depend on is
# actually present so we never flash an empty/fabricated kernel payload.
consume_kernel() {
    local img_gz="${KERNEL_OUT}/Image.gz"
    if [ ! -f "${img_gz}" ] || [ ! -s "${img_gz}" ]; then
        log_error "kernel Image.gz not found at ${img_gz}"
        log_error "The kernel build (bg-kernel) has not produced an image yet."
        log_error "Run kernel/build-kernel.sh first, then images/build.sh."
        return 1
    fi
    if [ -d "${KERNEL_OUT}/dtbs" ]; then
        local n
        n=$(find "${KERNEL_OUT}/dtbs" -type f 2>/dev/null | wc -l | tr -d ' ')
        log_info "kernel dtbs: ${n} file(s) under ${KERNEL_OUT}/dtbs"
    else
        log_warn "no dtbs/ under ${KERNEL_OUT} — using generic ARM64 boot path"
    fi
    log_ok "kernel payload present: ${img_gz}"
    return 0
}

# publish_boot_artifact(): stage the packaged artifacts + the consumed kernel
# pieces into the flashable dir so a later `fastboot flash` / UTM boot can use
# them together (kernel + initramfs + dtb + boot.img).
publish_boot_artifact() {
    ensure_boot_artifact
    consume_kernel || log_warn "kernel missing — publishing initramfs/boot chain only"
    mkdir -p "${FLASH_DIR}"
    local src=""
    for f in boot.img initramfs.cpio.gz Image.gz Image cmdline.txt; do
        src="${BOOT_ARTIFACT_DIR}/${f}"
        if [ -f "${src}" ]; then
            cp -f "${src}" "${FLASH_DIR}/${f}" 2>/dev/null || true
        fi
    done
    # copy any dtb the build unpacked
    for d in "${BOOT_ARTIFACT_DIR}"/*.dtb; do
        [ -f "${d}" ] && cp -f "${d}" "${FLASH_DIR}/" 2>/dev/null || true
    done
    log_ok "boot artifacts published to ${FLASH_DIR}"
}


main() {
    echo ""
    echo "=============================================="
    echo "  Nuxel Flash Tool — Immutable OS"
    echo "  Google Pixel 10 Pro XL (mustang)"
    echo "  Device key: ${NUXEL_DEVICE_KEY} (dir: ${NUXEL_DEVICE_DIR})"
    echo "  Serial: 58211FDCQ001LA"
    echo "=============================================="
    echo ""
    
    # --- boot-artifact chain: consume kernel + package boot.img + initramfs ---
    if [ "${DO_BUILD_BOOT}" -eq 1 ] || [ "${DO_PUBLISH_BOOT}" -eq 1 ]; then
        if [ "${DO_PUBLISH_BOOT}" -eq 1 ]; then
            publish_boot_artifact
        else
            ensure_boot_artifact
        fi
    fi


    check_fastboot
    check_device
    
    # Unlock / relock if requested
    [ "${DO_UNLOCK}" -eq 1 ] && unlock_bootloader
    if [ "${DO_RELOCK_CUSTOM}" -eq 1 ]; then
        relock_with_custom_key
    elif [ "${DO_RELOCK}" -eq 1 ]; then
        relock_bootloader
    fi
    
    select_slot
    
    # Generate flashable directory
    mkdir -p "$FLASH_DIR"
    
    # Find images
    for img in boot.img init_boot.img vendor_boot.img dtbo.img vbmeta.img system.img; do
        src="${BUILD_OUT}/${img}"
        if [ -f "$src" ] && [ ! -f "${FLASH_DIR}/${img}" ]; then
            ln -sf "$src" "${FLASH_DIR}/${img}" 2>/dev/null || cp "$src" "${FLASH_DIR}/"
        fi
    done
    
    # Pre-flight: verify ALL required images exist and are non-zero
    log_info "=== Pre-flight Check ==="
    local missing=0
    for img_pair in "boot.img:boot:1048576" "init_boot.img:init_boot:8192"                     "vendor_boot.img:vendor_boot:524288" "dtbo.img:dtbo:4096"                     "vbmeta.img:vbmeta:1024"; do
        IFS=':' read -r fname label minsize <<< "$img_pair"
        imgpath="${FLASH_DIR}/${fname}"
        [ ! -f "$imgpath" ] && imgpath="${BUILD_OUT}/${fname}"
        if [ -f "$imgpath" ]; then
            verify_image "$imgpath" "$fname" "$minsize"
        else
            log_error "${fname} not found (${label})"
            missing=1
        fi
    done
    
    if [ "${missing}" -eq 1 ]; then
        log_error ""
        log_error "============================================"
        log_error "  CANNOT FLASH: Required images missing"
        log_error "  Run: bash images/build.sh"
        log_error "  Nuxel v0.4.0-alpha produces DEV STUBS only."
        log_error "  Do NOT flash to hardware."
        log_error "============================================"
        exit 2
    fi
    
    log_ok "All required images present and valid"
    
    echo ""
    log_info "=== Flashing Sequence ==="
    echo ""
    
    # 1. VBmeta (must be first)
    echo "--- 1/6: AVB Verification ---"
    flash_vbmeta
    
    # 2. DTBO
    echo "--- 2/6: Device Tree Overlay ---"
    verify_image "${DTBO_IMG}" "dtbo.img" 4096 && {
        flash_image dtbo "${DTBO_IMG}" a
        flash_image dtbo "${DTBO_IMG}" b
    }
    
    # 3. Boot
    echo "--- 3/6: Boot Image ---"
    verify_image "${BOOT_IMG}" "boot.img" 1048576 && {
        flash_image boot "${BOOT_IMG}" a
        flash_image boot "${BOOT_IMG}" b
    }
    
    # 4. Init Boot
    echo "--- 4/6: Init Boot ---"
    verify_image "${INIT_BOOT_IMG}" "init_boot.img" 131072 && {
        flash_image init_boot "${INIT_BOOT_IMG}" a
        flash_image init_boot "${INIT_BOOT_IMG}" b
    }
    
    # 5. Vendor Boot
    echo "--- 5/6: Vendor Boot ---"
    verify_image "${VENDOR_BOOT_IMG}" "vendor_boot.img" 524288 && {
        flash_image vendor_boot "${VENDOR_BOOT_IMG}" a
        flash_image vendor_boot "${VENDOR_BOOT_IMG}" b
    }
    
    # 6. System (via fastbootd with dm-verity)
    echo "--- 6/6: System Image (dm-verity) ---"
    flash_system_dmverity
    
    # Set active and wipe
    log_info "Setting active slot to ${TARGET_SLOT}..."
    fastboot set_active "${TARGET_SLOT}"
    
    if [ "${DO_WIPE}" -eq 1 ]; then
        log_info "Wiping userdata..."
        echo -n "Confirm wipe? [y/N] "
        read -r ans; [ "${ans}" = "y" ] && fastboot -w
    fi
    
    echo ""
    log_ok "======================================"
    log_ok "  Flash complete!"
    log_ok "======================================"
    echo ""
    log_info "Active slot: ${TARGET_SLOT}"
    log_info "dm-verity:   $([ -n "${SYSTEM_IMG}" ] && echo "ENABLED" || echo "N/A")"
    log_info "AVB:         $([ "${SKIP_AVB}" -eq 1 ] && echo "SKIPPED" || echo "$([ "${PRODUCTION}" -eq 1 ] && echo 'PRODUCTION' || echo 'DEVELOPMENT')")"
    echo ""
    
    if [ "${NO_REBOOT}" -eq 1 ]; then
        log_info "Done. Run: fastboot reboot"
    else
        log_info "Rebooting in 3 seconds..."
        sleep 3
        fastboot reboot
    fi
    echo ""
    log_info "First boot takes ~35 seconds."
    log_info "If no display: wait up to 10s for AMB655X panel init."
    log_info "Bootloop: Hold Vol Down + Power for 15s → re-flash."
}

main "$@"
