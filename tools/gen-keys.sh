#!/bin/bash
# Nuxel Verified Boot Key Generation
# Generates keys for AVB signing and dm-verity root hash signing
#
# Output:
#   keys/nuxel-avb.pem           — RSA 4096 private key for AVB
#   keys/nuxel-avb-public.bin    — Public key for bootloader enrollment
#   keys/nuxel-avb.material      — Key metadata
#   keys/nuxel-verity.pem        — ECDSA P-256 for dm-verity
#   keys/README.md               — Key management instructions
#
# Target: mustang (Pixel 10 Pro XL) with Titan M3

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
ALGORITHM="SHA256_RSA4096"
AVB_KEY="${KEYS_DIR}/nuxel-avb.pem"
AVB_PUBLIC="${KEYS_DIR}/nuxel-avb-public.bin"
VERITY_KEY="${KEYS_DIR}/nuxel-verity.pem"
METADATA="${KEYS_DIR}/nuxel-avb.material"

# Resolve avbtool: prefer one on PATH, else the in-repo copy
# (external/avbtool/avbtool, fetched from AOSP during the prep pass).
resolve_avbtool() {
    if command -v avbtool >/dev/null 2>&1; then
        AVBTOOL="avbtool"
    elif [ -x "${NUXXEL_ROOT}/external/avbtool/avbtool" ]; then
        AVBTOOL="${NUXXEL_ROOT}/external/avbtool/avbtool"
    elif [ -f "${NUXXEL_ROOT}/external/avbtool/avbtool.py" ]; then
        AVBTOOL="python3 ${NUXXEL_ROOT}/external/avbtool/avbtool.py"
    else
        AVBTOOL=""
    fi
}

check_dependencies() {
    local missing=0

    for cmd in openssl python3; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "Missing dependency: $cmd"
            missing=1
        fi
    done

    resolve_avbtool
    if [ -z "${AVBTOOL}" ]; then
        log_error "Missing dependency: avbtool"
        missing=1
    fi

    if [ "$missing" -eq 1 ]; then
        log_error "Install missing dependencies:"
        log_error "  openssl: apt install openssl   (macOS: brew install openssl)"
        log_error "  avbtool: apt install avbtool   (or use external/avbtool/avbtool)"
        exit 1
    fi
}

generate_avb_key() {
    log_info "Generating AVB signing key (RSA 4096)..."
    
    if [ -f "$AVB_KEY" ]; then
        log_warn "AVB key already exists at ${AVB_KEY}"
        echo -n "Overwrite? [y/N] "
        read -r answer
        if [ "${answer}" != "y" ] && [ "${answer}" != "Y" ]; then
            log_info "Keeping existing key"
            return 0
        fi
    fi
    
    mkdir -p "$KEYS_DIR"
    
    # Generate RSA 4096 private key
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 \
        -out "$AVB_KEY" -aes-256-cbc
    
    # Extract public key in AVB format
    # shellcheck disable=SC2086  # $AVBTOOL may be "python3 /path/avbtool.py"
    ${AVBTOOL} extract_public_key --key "$AVB_KEY" \
        --output "$AVB_PUBLIC"
    
    # Create key metadata
    cat > "$METADATA" << EOF
Nuxel AVB Signing Key
Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Algorithm: ${ALGORITHM}
Key size: 4096 bits
Format: PEM (PKCS#8)
Device: Google Pixel 10 Pro XL (mustang)
Serial: 58211FDCQ001LA

This key signs boot.img, system.img, and vbmeta.img for
verified boot. The public key should be enrolled in the
bootloader for production relocking.

DO NOT LOSE THIS KEY. Without it, you cannot:
- Sign new OS updates
- Relock the bootloader
- Recover the device if bootloader is relocked

Store a backup offline (USB drive, printed QR code).
EOF
    
    chmod 600 "$AVB_KEY"
    chmod 644 "$AVB_PUBLIC"
    chmod 600 "$METADATA"
    
    log_ok "AVB signing key generated: ${AVB_KEY}"
    log_ok "Public key: ${AVB_PUBLIC}"
}

generate_verity_key() {
    log_info "Generating dm-verity signing key (ECDSA P-256)..."
    
    if [ -f "$VERITY_KEY" ]; then
        log_warn "Verity key already exists at ${VERITY_KEY}"
        echo -n "Overwrite? [y/N] "
        read -r answer
        if [ "${answer}" != "y" ] && [ "${answer}" != "Y" ]; then
            log_info "Keeping existing key"
            return 0
        fi
    fi
    
    # Generate ECDSA P-256 key for dm-verity
    openssl ecparam -genkey -name prime256v1 -out "$VERITY_KEY"
    chmod 600 "$VERITY_KEY"
    
    log_ok "dm-verity signing key generated: ${VERITY_KEY}"
}

generate_gitignore() {
    local gitignore="${KEYS_DIR}/.gitignore"
    cat > "$gitignore" << 'EOF'
# Nuxel signing keys — DO NOT COMMIT
*.pem
*.bin
*.material
*.key
*.pub
*.bak
# Keep README.md and .gitignore
!.gitignore
!README.md
EOF
    log_ok "Gitignore updated for keys directory"
}

generate_readme() {
    local readme="${KEYS_DIR}/README.md"
    cat > "$readme" << 'MDEOF'
# Nuxel Signing Keys

## WARNING
**These keys are the root of trust for your Nuxel device.**
**Loss of these keys means permanent loss of the ability to:**
- Sign OS updates
- Relock the bootloader
- Recover from a relocked state

## Key Files

| File | Purpose |
|------|---------|
| `nuxel-avb.pem` | RSA 4096 private key for AVB image signing |
| `nuxel-avb-public.bin` | Public key for bootloader enrollment |
| `nuxel-verity.pem` | ECDSA P-256 key for dm-verity root hash signing |
| `nuxel-avb.material` | Key metadata and generation info |

## Enrollment

To enroll your public key in the bootloader and relock:

```bash
fastboot oem avb_set_key keys/nuxel-avb-public.bin
fastboot flashing lock
```

**This is irreversible without your private key.**

## Backup

Store offline backups:
```bash
# Encrypted USB drive
tar czf nuxel-keys-backup.tar.gz keys/
gpg -c nuxel-keys-backup.tar.gz

# Print as QR code (for disaster recovery)
cat keys/nuxel-avb.pem | paperkey --output-type qr > keys-backup.png
```
MDEOF
    log_ok "README written: ${readme}"
}

show_summary() {
    echo ""
    log_info "======================================"
    log_info "  Key Generation Complete"
    log_info "======================================"
    echo ""
    log_ok "AVB key:          ${AVB_KEY}"
    log_ok "AVB public:       ${AVB_PUBLIC}"
    log_ok "Verity key:       ${VERITY_KEY}"
    log_ok "Metadata:         ${METADATA}"
    echo ""
    log_warn "IMPORTANT: Store these keys securely!"
    log_warn "Backup: tar czf nuxel-keys-backup.tar.gz keys/"
    echo ""
    log_info "To enroll and relock the bootloader:"
    log_info "  1. fastboot oem avb_set_key ${AVB_PUBLIC}"
    log_info "  2. fastboot flashing lock"
    echo ""
}

# Main
echo ""
echo "======================================"
echo "  Nuxel Key Generation Tool"
echo "  Device: Pixel 10 Pro XL (mustang)"
echo "  Serial: 58211FDCQ001LA"
echo "======================================"
echo ""

check_dependencies
generate_avb_key
generate_verity_key
generate_gitignore
generate_readme
show_summary
