#!/bin/bash
# Nuxel Image Signing Script
# Signs boot.img, system.img (dm-verity), and creates vbmeta.img
#
# Usage:
#   ./tools/sign-image.sh boot <boot.img>     — Sign boot image
#   ./tools/sign-image.sh system <system.img>  — Create dm-verity + sign
#   ./tools/sign-image.sh all                   — Sign everything
#   ./tools/sign-image.sh vbmeta               — Create vbmeta chaining all

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

NUXXEL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KEYS_DIR="${NUXXEL_ROOT}/keys"
BUILD_OUT="${NUXXEL_ROOT}/build/out"
AVB_KEY="${KEYS_DIR}/nuxel-avb.pem"
AVB_PUBLIC="${KEYS_DIR}/nuxel-avb-public.bin"
VERITY_KEY="${KEYS_DIR}/nuxel-verity.pem"
AVB_ALGORITHM="SHA256_RSA4096"
ROLLBACK_INDEX=1

check_dependencies() {
    local missing=0
    for cmd in openssl avbtool veritysetup; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "Missing dependency: $cmd"
            missing=1
        fi
    done
    
    if [ ! -f "$AVB_KEY" ]; then
        log_error "AVB key not found at ${AVB_KEY}"
        log_error "Run ./tools/gen-keys.sh first"
        missing=1
    fi
    
    if [ "$missing" -eq 1 ]; then
        exit 1
    fi
    
    log_ok "All dependencies found"
}

sign_boot() {
    local boot_img="${1:-${BUILD_OUT}/boot.img}"
    local boot_signed="${boot_img}.signed"
    
    if [ ! -f "$boot_img" ]; then
        log_error "boot.img not found at ${boot_img}"
        return 1
    fi
    
    log_info "Signing boot image: ${boot_img}"
    
    avbtool add_hash_footer \
        --image "$boot_img" \
        --partition_name boot \
        --partition_size "$((96 * 1024 * 1024))" \
        --key "$AVB_KEY" \
        --algorithm "$AVB_ALGORITHM" \
        --rollback_index "$ROLLBACK_INDEX" \
        --output "$boot_signed"
    
    log_ok "Signed boot image: ${boot_signed}"
    
    # Copy signed version back to original location if requested
    echo "$boot_signed"
}

sign_system() {
    local system_img="${1:-${BUILD_OUT}/system.img}"
    local verity_data="${system_img}.verity"
    local root_hash_file="${BUILD_OUT}/system.root_hash"
    
    if [ ! -f "$system_img" ]; then
        log_error "system.img not found at ${system_img}"
        return 1
    fi
    
    log_info "Creating dm-verity hash tree for system image..."
    
    # Generate dm-verity hash tree
    local root_hash
    root_hash=$(veritysetup format \
        --hash=sha256 \
        --salt="$(openssl rand -hex 32)" \
        "$system_img" \
        "$verity_data" 2>&1 | grep 'Root hash:' | awk '{print $3}')
    
    echo "$root_hash" > "$root_hash_file"
    log_ok "dm-verity root hash: ${root_hash}"
    log_ok "Verity data: ${verity_data}"
    
    # Get system image size
    local system_size
    system_size=$(stat -f%z "$system_img" 2>/dev/null || stat -c%s "$system_img" 2>/dev/null)
    
    log_info "Adding AVB hash footer to system image..."
    
    avbtool add_hash_footer \
        --image "$system_img" \
        --partition_name system \
        --partition_size "$system_size" \
        --hash_algorithm sha256 \
        --salt "$(openssl rand -hex 32)" \
        --output "$system_img.signed"
    
    log_ok "System image signed with AVB hash footer"
}

create_vbmeta() {
    local boot_img="${1:-${BUILD_OUT}/boot.img.signed}"
    local system_img="${2:-${BUILD_OUT}/system.img}"
    local vbmeta_img="${BUILD_OUT}/vbmeta.img"
    
    log_info "Creating vbmeta image chaining boot and system..."
    
    # If we have a signed boot image, chain descriptors from it
    local include_args=""
    if [ -f "${boot_img}" ]; then
        include_args="$include_args --include_descriptors_from_image ${boot_img}"
    fi
    if [ -f "${system_img}" ]; then
        include_args="$include_args --include_descriptors_from_image ${system_img}"
    fi
    
    avbtool make_vbmeta_image \
        $include_args \
        --key "$AVB_KEY" \
        --algorithm "$AVB_ALGORITHM" \
        --rollback_index "$ROLLBACK_INDEX" \
        --flags 0 \
        --padding_size 4096 \
        --output "$vbmeta_img"
    
    log_ok "vbmeta created: ${vbmeta_img}"
    
    # Also create a development vbmeta with verification disabled
    local vbmeta_dev="${BUILD_OUT}/vbmeta-dev.img"
    avbtool make_vbmeta_image \
        --flags 2 \
        --padding_size 4096 \
        --output "$vbmeta_dev"
    
    log_ok "Development vbmeta (verification disabled): ${vbmeta_dev}"
}

sign_all() {
    log_info "=== Signing all images ==="
    echo ""
    
    sign_boot "${BUILD_OUT}/boot.img"
    sign_system "${BUILD_OUT}/system.img"
    create_vbmeta "${BUILD_OUT}/boot.img.signed" "${BUILD_OUT}/system.img"
    
    echo ""
    log_ok "=== All images signed ==="
    ls -lh "${BUILD_OUT}/"*.signed "${BUILD_OUT}/vbmeta.img" "${BUILD_OUT}/system.img.verity" 2>/dev/null
}

verify_signed() {
    local image="${1}"
    
    if [ ! -f "$image" ]; then
        log_error "File not found: $image"
        return 1
    fi
    
    log_info "Verifying: $image"
    avbtool verify_image --image "$image" || {
        log_error "Verification FAILED for $image"
        return 1
    }
    log_ok "Verification passed: $image"
}

# Parse command
case "${1:-help}" in
    boot)
        sign_boot "${2:-${BUILD_OUT}/boot.img}"
        ;;
    system)
        sign_system "${2:-${BUILD_OUT}/system.img}"
        ;;
    vbmeta)
        create_vbmeta "${2:-${BUILD_OUT}/boot.img.signed}" "${3:-${BUILD_OUT}/system.img}"
        ;;
    all)
        sign_all
        ;;
    verify)
        verify_signed "${2}"
        ;;
    *)
        echo "Nuxel Image Signing Tool"
        echo ""
        echo "Usage:"
        echo "  $0 boot [boot.img]         Sign boot image"
        echo "  $0 system [system.img]     Create dm-verity + sign system"
        echo "  $0 vbmeta [boot] [system]  Create vbmeta chaining all"
        echo "  $0 all                      Sign everything"
        echo "  $0 verify <image>           Verify a signed image"
        echo ""
        echo "Keys: ${KEYS_DIR}/"
        echo "Output: ${BUILD_OUT}/"
        ;;
esac
