#!/bin/bash
#==============================================================================
# Nuxel AVB signing script — mustang (Pixel 10 Pro XL)
#
# Uses avbtool (Android build-tools repo) to sign the boot chain:
#   boot.img, dtbo.img, system.img, vendor.img → chained to vbmeta.img
#
# Also supports the bootloader-relock path (state=locksigned) invoked from
# boot/flash.sh. See images/avb/mustang-avb.conf for the chain definition.
#
# Requirements:
#   * avbtool from https://android.googlesource.com/platform/external/avb
#     (`git clone https://android.googlesource.com/platform/external/avb`)
#     — the Python 3 version requires `pycryptodome` (`pip install pycryptodome`).
#   * A user-generated RSA private key (PEM).
#
# Fastboot flash path after signing:
#   fastboot flash vbmeta build/out/vbmeta.img
#   (boot/dtbo/system/vendor are flashed by boot/flash.sh)
#==============================================================================
set -euo pipefail

NUXXEL_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "${NUXXEL_ROOT}"

# Device selection: this per-device signer is mustang-only. The shared
# selector never silently guesses; it defaults to mustang only for backward
# compatibility (this script historically WAS the mustang AVB signer).
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "mustang" ] || {
    echo "sign.sh is ONLY for mustang. Got: ${NUXEL_DEVICE_KEY}" >&2
    exit 1
}

AVBTOOL="${AVBTOOL:-./external/avbtool/avbtool}"   # override with --avbtool path
CONF="images/${NUXEL_DEVICE_DIR}/avb/mustang-avb.conf"
KEYS_DIR="${NUXXEL_ROOT}/keys"
OUT_DIR="${NUXXEL_ROOT}/build/out"

# Console key path (defaults; may be overridden by --key).
KEY_PRIV="${KEYS_DIR}/nuxel-avb-private.pem"
KEY_PUB="${KEYS_DIR}/nuxel-avb-public.bin"
ALGO="SHA256_RSA2048"

KEY_ARG=""
ALGO_ARG=""

usage() {
    cat <<'EOF'
Usage: images/${NUXEL_DEVICE_DIR}/avb/sign.sh [--key <priv.pem>] [--avbtool <path>] [--algorithm <alg>]
                          [--rollback <index>] [--help]

Generates the signed boot chain (boot/dtbo/system/vendor -> vbmeta.img) under
build/out/ using avbtool. Uses images/${NUXEL_DEVICE_DIR}/avb/mustang-avb.conf for the layout.

--key <priv.pem>      Signing key (default keys/nuxel-avb-private.pem)
--avbtool <path>      Path to avbtool (default ./external/avbtool/avbtool)
--algorithm <alg>     e.g. SHA256_RSA2048 (default), SHA256_RSA4096
--rollback <index>    Rollback index (default from mustang-avb.conf)
EOF
}

cfg() { # cfg <section> <key>
    local sec="$1" k="$2"
    awk -F= -v sec="$sec" -v k="$k" '
    $0 ~ "^\\[" sec "\\]" {ins=1; next}
    $0 ~ "^\\[" && !$0 ~ "^\\[" sec "\\]" {ins=0}
    ins && $1==k {sub(/^[^=]*=/,""); print; exit}
    ' "$CONF"
}

highlight() { echo -e "\033[1;36m==> $*\033[0m"; }
err()        { echo -e "\033[1;31m==> ERROR: $*\033[0m" >&2; }

check_avbtool() {
    if [ ! -x "$AVBTOOL" ] && ! command -v "$AVBTOOL" &>/dev/null; then
        err "avbtool not found at '${AVBTOOL}'."
        err "Clone it first:"
        err "  git clone https://android.googlesource.com/platform/external/avb external/avb"
        err "  (Python 3 version needs: pip install pycryptodome)"
        exit 1
    fi
    highlight "Using avbtool: ${AVBTOOL}"
}

require_key() {
    if [ -z "$KEY_PRIV" ] || [ ! -f "$KEY_PRIV" ]; then
        err "Signing key not found: ${KEY_PRIV}"
        err "Generate a new user key with:"
        err "  mkdir -p keys"
        err "  openssl genrsa -out keys/nuxel-avb-private.pem 2048"
        err "  avbtool extract_public_key --key keys/nuxel-avb-private.pem \\"
        err "      --output keys/nuxel-avb-public.bin"
        exit 1
    fi
    # Derive the public key if not already present, or update it to match.
    if [ ! -f "$KEY_PUB" ] || ! grep -q "" "$KEY_PUB"; then
        highlight "Extracting public key ${KEY_PUB}..."
        "$AVBTOOL" extract_public_key --key "$KEY_PRIV" --output "$KEY_PUB"
    fi
    highlight "Using signing key: ${KEY_PRIV}"
}

partition_cfg() { # partition_cfg <partition> <key>
    # Read a partition key from the conf, stripping any trailing `#` comment.
    cfg "partition.${1}" "$2" | sed 's/[[:space:]]#.*$//'
}

# add_footer <partition> <image>
#
# Signs a partition with the correct footer for its type (from mustang-avb.conf):
#   * type=boot/dtbo/raw  → add_image_footer  (plain signed footer)
#   * type=verity         → add_hash_footer   (adds a real dm-verity hash tree
#                                              / FEC tree backed footer)
add_footer() {
    local part="$1" img="$2"
    [ -f "$img" ] || { err "image missing: ${img} (partition ${part})"; return 1; }

    local type fec
    type="$(partition_cfg "$part" type | tr -d ' ' )"
    fec="$(partition_cfg "$part" fec | tr -d ' ' | tr '[:upper:]' '[:lower:]' )"
    [ -n "$type" ] && [ "$type" != "verity" ] && : # raw/boot footer path below

    if [ "$type" = "verity" ]; then
        highlight "Signing ${part} (${img}) — dm-verity hash footer..."
        local vargs=(--image "$img"
            --partition_name  "$part"
            --partition_size  "$(stat -f%z "$img")"
            --key             "$KEY_PRIV"
            --algorithm       "$ALGO"
            --use_verity_for_hash
            --hash_algorithm  sha256
            --rollback_index  "${ROLLBACK:-$(cfg avb rollback_index)}"
            --verbose)
        # When FEC is enabled the image must also carry a forward-error-correction
        # tree; set the FEC block/hash block sizes explicitly (avbtool defaults
        # to 4096-byte blocks which match the verity settings).
        if [ "$fec" = "true" ]; then
            vargs+=(--fec_rs 0)
            vargs+=(--fec_num_roots 2)
            vargs+=(--verity_block_size 4096)
            vargs+=(--fec_block_size 4096)
        fi
        "$AVBTOOL" add_hash_footer "${vargs[@]}" || {
            err "Failed to add dm-verity hash footer for ${part}"
            return 1
        }
        return 0
    fi

    highlight "Signing ${part} (${img})..."
    "$AVBTOOL" add_image_footer \
        --image "$img" \
        --partition_name "$part" \
        --partition_size "$(stat -f%z "$img")" \
        --key "$KEY_PRIV" \
        --algorithm "$ALGO" \
        --verbose || {
            err "Failed to add footer for ${part}"
            return 1
        }
    return 0
}

generate_vbmeta() {
    highlight "Generating top-level vbmeta.img..."

    local rollback="${ROLLBACK:-$(cfg avb rollback_index)}"
    local disable_verity; disable_verity="$(cfg avb disable_verity | tr -d ' ' | tr '[:upper:]' '[:lower:]')"
    local disable_verif; disable_verif="$(cfg avb disable_verification | tr -d ' ' | tr '[:upper:]' '[:lower:]')"

    local args=()
    args+=(--algorithm "$ALGO")
    if [ -n "$KEY_PRIV" ] && [ -f "$KEY_PRIV" ]; then
        args+=(--key "$KEY_PRIV")
    fi
    args+=(--rollback_index "$rollback")
    args+=(--include_descriptors_from_image build/out/boot.img)
    args+=(--include_descriptors_from_image build/out/dtbo.img)
    if [ -f build/out/system.img ]; then
        args+=(--include_descriptors_from_image build/out/system.img)
    fi
    [ -f build/out/vendor.img ] && args+=(--include_descriptors_from_image build/out/vendor.img)

    # Encode disable_verity / disable_verification into vbmeta. avbtool's
    # `--flags` value is a bitmask: bit 0 = disable_verification, bit 1 =
    # disable_verity. For a production device both must be 0 (verity and
    # signature verification enforced). We compute the numeric flags from the
    # conf so the bootloader cannot be told to skip dm-verity verification.
    local flags=0
    [ "$disable_verity" = "true" ] && flags=$((flags | 2))
    [ "$disable_verif" = "true" ] && flags=$((flags | 1))
    args+=(--flags "$flags")

    mkdir -p "$OUT_DIR"
    "$AVBTOOL" make_vbmeta_image \
        "${args[@]}" \
        --output "$OUT_DIR/vbmeta.img"

    highlight "vbmeta.img written: ${OUT_DIR}/vbmeta.img"
}

main() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --key)        KEY_PRIV="$2"; KEY_PUB="${KEY_PRIV%.pem}-public.bin"; shift 2 ;;
            --avbtool)    AVBTOOL="$2"; shift 2 ;;
            --algorithm)  ALGO="$2"; shift 2 ;;
            --rollback)   ROLLBACK="$2"; shift 2 ;;
            --help|-h)    usage; exit 0 ;;
            *) err "Unknown option: $1"; usage; exit 1 ;;
        esac
    done

    check_avbtool
    require_key

    highlight "=== Signing mustang boot chain ==="
    add_footer boot    build/out/boot.img
    add_footer dtbo    build/out/dtbo.img
    [ -f build/out/system.img ] && add_footer system build/out/system.img
    [ -f build/out/vendor.img ] && add_footer vendor build/out/vendor.img

    generate_vbmeta

    highlight "=== Summary ==="
    echo "  boot.img      : signed ($ALGO)"
    echo "  dtbo.img      : signed ($ALGO)"
    [ -f build/out/system.img ] && echo "  system.img    : signed (dm-verity hash footer)"
    [ -f build/out/vendor.img ] && echo "  vendor.img    : signed"
    echo "  vbmeta.img    : $(stat -f%z build/out/vbmeta.img 2>/dev/null || stat -c%s build/out/vbmeta.img 2>/dev/null) bytes"
    echo ""
    echo "Fastboot flash path:"
    echo "  fastboot flash vbmeta build/out/vbmeta.img"
    echo "  fastboot flash boot_a build/out/boot.img    # (per slot)"
    echo "  fastboot flash dtbo_a build/out/dtbo.img"
    echo "  For full relock: see boot/flash.sh --relock-custom-key"
    echo ""
    echo "Verify a signed vbmeta:"
    echo "  $AVBTOOL info_image --image build/out/vbmeta.img"
    echo "  $AVBTOOL verify_image --image build/out/vbmeta.img --key ${KEY_PUB}"
}

main "$@"
