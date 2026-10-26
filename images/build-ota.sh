#!/bin/bash
#==============================================================================
# Nuxel OTA build script
#
# Produces an atomic, signed update artifact for the requested target:
#
#   --target pmos   → RAUC bundle (.raucb) for mustang / postmarketOS
#   --target fedora → OSTree commit pushed to the Fedora ARM64 VM repo
#
# See docs/update-strategy.md for the full policy and images/rauc and
# images/ostree for the per-target configuration.
#
# Requirements:
#   * pmos  : `rauc` CLI installed on the host, a signing key in keys/
#   * fedora: `ostree` + `rpm-ostree` installed, a compose tree available
#
# Usage examples:
#   bash images/build-ota.sh --target pmos --version 0.1.1 \
#       --rootfs build/out/rootfs.ext4 --boot build/out/boot.img
#   bash images/build-ota.sh --target fedora --version 0.1.1
#==============================================================================
set -euo pipefail

NUXXEL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${NUXXEL_ROOT}"

# Device selection: this OTA builder historically targeted the mustang tree,
# so it defaults to mustang when no explicit --device/NUXEL_DEVICE is given
# (the shared selector itself never silently guesses). Per-device configs
# (images/rauc, images/ostree) resolve via ${NUXEL_DEVICE_DIR}.
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXXEL_ROOT}/tools/nuxel-device-select.sh" "$@"

OUT_DIR="${NUXXEL_ROOT}/build/out"
KEYS_DIR="${NUXXEL_ROOT}/keys"
RAUC_CONFIG="${NUXXEL_ROOT}/images/${NUXEL_DEVICE_DIR}/rauc/mustang-system-bundle.conf"
RAUC_TEMPLATE="${NUXXEL_ROOT}/images/${NUXEL_DEVICE_DIR}/rauc/rauc-config.in"

TARGET=""
VERSION="0.6.5-beta"
KEY=""
ROOTFS_IMG=""
BOOT_IMG=""
HOOKS_TAR=""
COMPOSE_HOST="${NUXXEL_ROOT}/images/${NUXEL_DEVICE_DIR}/ostree"

usage() {
    cat <<'EOF'
Usage: images/build-ota.sh [options]

Options:
  --device <key>           device key (default: mustang)
  --target <pmos|fedora>   Update mechanism to build
  --version <ver>          Version string, e.g. 0.1.1 (default: 0.6.5-beta)
  --key <path>             Signing key (RAUC private key or OSTree GPG keyring)
  --rootfs <path>          Root filesystem image (pmos only)
  --boot <path>            Boot image (pmos only, optional)
  --hooks-tar <path>       Optional RAUC hooks payload tarball (pmos only)
  --help                   Show this help
EOF
}

sha256() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}' || sha256sum "$1" | awk '{print $1}'; }

highlight() { echo -e "\033[1;36m==> $*\033[0m"; }
err()        { echo -e "\033[1;31m==> ERROR: $*\033[0m" >&2; }
log_warn()   { echo -e "\033[1;33m==> WARN: $*\033[0m" >&2; }

#------------------------------------------------------------------------------
# RAUC (pmOS) path
#------------------------------------------------------------------------------
build_pmos() {
    if ! command -v rauc &>/dev/null; then
        err "RAUC CLI not found. Install rauc (e.g. 'apt install rauc' or build from source)."
        exit 1
    fi

    [ -n "${ROOTFS_IMG}" ] || { err "--rootfs is required for --target pmos"; exit 1; }
    [ -f "${ROOTFS_IMG}" ] || { err "Rootfs image not found: ${ROOTFS_IMG}"; exit 1; }

    local cert=""
    if [ -n "${KEY}" ]; then
        cert="${KEY%.pem}.cert.pem"
        [ -f "${cert}" ] || cert="${KEYS_DIR}/rauc-cert.pem"
    else
        KEY="${KEYS_DIR}/rauc-dev.key.pem"
        cert="${KEYS_DIR}/rauc-cert.pem"
    fi

    if [ ! -f "${KEY}" ]; then
        err "RAUC signing key not found: ${KEY}"
        err "Generate one first:  see docs/update-strategy.md §1.3"
        err "  openssl genpkey -algorithm ED25519 -out ${KEY}"
        err "  (and export the matching cert)"
        exit 1
    fi

    highlight "Verifying bundle descriptor template..."
    [ -f "${RAUC_TEMPLATE}" ] || { err "Missing ${RAUC_TEMPLATE}"; exit 1; }

    local workdir
    workdir="$(mktemp -d)"
    trap 'rm -rf "${workdir}"' EXIT

    # Expand the template markers to concrete artifacts.
    local rauc_rootfs_sha rauc_boot_sha rauc_hooks_sha=""
    rauc_rootfs_sha="$(sha256 "${ROOTFS_IMG}")"
    local boot_line=""
    if [ -n "${BOOT_IMG}" ] && [ -f "${BOOT_IMG}" ]; then
        rauc_boot_sha="$(sha256 "${BOOT_IMG}")"
        boot_line="boot"
    fi
    local hooks_line=""
    if [ -n "${HOOKS_TAR}" ] && [ -f "${HOOKS_TAR}" ]; then
        rauc_hooks_sha="$(sha256 "${HOOKS_TAR}")"
        hooks_line="hooks"
    fi

    sed -e "s|@@VERSION@@|${VERSION}|g" \
        -e "s|@@IMG_ROOTFS@@|${ROOTFS_IMG}|g" \
        -e "s|@@IMG_ROOTFS_SHA256@@|${rauc_rootfs_sha}|g" \
        -e "s|@@IMG_BOOT@@|${BOOT_IMG:-/dev/null}|g" \
        -e "s|@@IMG_BOOT_SHA256@@|${rauc_boot_sha:-unset}|g" \
        -e "s|@@IMG_FIRMWARE@@|/dev/null|g" \
        -e "s|@@IMG_FIRMWARE_SHA256@@|unset|g" \
        -e "s|@@HOOKS_TAR@@|${HOOKS_TAR:-/dev/null}|g" \
        -e "s|@@HOOKS_SHA256@@|${rauc_hooks_sha:-unset}|g" \
        "${RAUC_TEMPLATE}" > "${workdir}/rauc-config"

    # Strip comments/blank lines around the optional boot/hooks sections we
    # did not fill in, so `rauc bundle` does not error on empty filenames.
    if [ -z "${boot_line}" ]; then
        sed -e '/^\[image\.boot\]/,/^$/d' -i '' "${workdir}/rauc-config" 2>/dev/null \
            || sed -e '/^\[image\.boot\]/,/^$/d' -i "${workdir}/rauc-config"
        # Remove the boot section entirely (best-effort POSIX rewrite)
        awk '
            BEGIN{skip=0}
            /^\[image.boot\]/{skip=1; next}
            skip && /^\[/{skip=0}
            !skip {print}
        ' "${workdir}/rauc-config" > "${workdir}/rauc-config.clean"
        mv "${workdir}/rauc-config.clean" "${workdir}/rauc-config"
    fi
    if [ -z "${hooks_line}" ]; then
        awk '
            BEGIN{skip=0}
            /^\[hooks\]/{skip=1; next}
            skip && /^\[/{skip=0}
            !skip {print}
        ' "${workdir}/rauc-config" > "${workdir}/rauc-config.clean"
        mv "${workdir}/rauc-config.clean" "${workdir}/rauc-config"
    fi
    [ -z "${boot_line}" ] && [ -z "${hooks_line}" ] && {
        # Remove the now-orphaned [image.rootfs] trailing assets safely.
        :
    }

    highlight "Assembling RAUC bundle..."
    local bundle="${OUT_DIR}/nuxel-mustang-${VERSION}.raucb"
    mkdir -p "${OUT_DIR}"
    # Bundle-embedded verification keyring. RAUC bundles are verified with the
    # cert/key used to sign; an optional public keyring can be embedded so the
    # bundle carries a shared verification root. --signing-keyring is NOT a
    # valid `rauc bundle` option, so we only pass --keyring when the generated
    # public keyring actually exists (see docs/update-strategy.md §1.3).
    local keyring_arg=()
    if [ -f "${KEYS_DIR}/rauc-public-keyring.pem" ]; then
        keyring_arg=(--keyring "${KEYS_DIR}/rauc-public-keyring.pem")
    else
        log_warn "keys/rauc-public-keyring.pem not found; bundling without a bundle-embedded keyring (bundle still signed by --cert/--key)."
    fi
    rauc bundle \
        --cert "${cert}" \
        --key  "${KEY}" \
        "${keyring_arg[@]}" ${ENABLE_LIST:+"${ENABLE_LIST}"} \
        "${workdir}/rauc-config" \
        "${bundle}"

    highlight "RAUC bundle written: ${bundle}"
    rauc info "${bundle}" || true
    echo ""
    echo "Verify metadata against images/${NUXEL_DEVICE_DIR}/rauc/mustang-system-bundle.conf (compatible=nuxel-mustang)."
}

#------------------------------------------------------------------------------
# OSTree (Fedora VM) path
#------------------------------------------------------------------------------
build_fedora() {
    if ! command -v ostree &>/dev/null; then
        err "ostree CLI not found. Install ostree + rpm-ostree."
        exit 1
    fi

    local repo="${NUXXEL_ROOT}/build/ostree-repo"
    local treefile="${COMPOSE_HOST}/nuxel-vm-treefile.yaml"

    [ -f "${treefile}" ] || { err "Missing compose tree: ${treefile}"; exit 1; }

    highlight "Initializing OSTree repo if needed..."
    if [ ! -d "${repo}/objects" ]; then
        ostree --repo="${repo}" init --mode=archive
    fi

    highlight "Composing tree (this can take a long time)..."
    if command -v rpm-ostree &>/dev/null; then
        sudo rpm-ostree compose tree --repo="${repo}" "${treefile}"
    else
        err "rpm-ostree not installed on this host; OSTree compose is not possible."
        exit 1
    fi

    highlight "Signing commit..."
    local ref="nuxel/fedora/arm64/utm"
    if [ -n "${KEY}" ] && [ -f "${KEY}" ]; then
        local fp
        fp="$(gpg --with-colons --import-options show-only --import "${KEY}" 2>/dev/null \
            | awk -F: '$1=="fpr"{print $10; exit}')"
        if [ -n "${fp}" ]; then
            ostree --repo="${repo}" commit \
                --gpg-sign="${fp}" \
                -b "${ref}" \
                --subject "Nuxel VM ${VERSION}" \
                ${EXTRA_COMMIT_ARGS:+"${EXTRA_COMMIT_ARGS}"} 2>/dev/null || {
                # If there is nothing new to commit, re-sign the existing ref.
                ostree --repo="${repo}" commit --gpg-sign="${fp}" -b "${ref}" \
                    --tree=ref="${ref}" --subject "Nuxel VM ${VERSION}" \
                    || true
            }
        else
            ostree --repo="${repo}" commit -b "${ref}" \
                --subject "Nuxel VM ${VERSION}" || true
        fi
    else
        ostree --repo="${repo}" commit -b "${ref}" \
            --subject "Nuxel VM ${VERSION}" || true
    fi

    highlight "OSTree repo populated: ${repo}"
    ostree --repo="${repo}" log "${ref}" | head -20 || true
    echo ""
    echo "Next steps for the VM:"
    echo "  sudo ostree --repo=/ostree/repo pull file://${repo} ${ref}"
    echo "  sudo rpm-ostree deploy ${ref}@<commit>"
    echo "  sudo systemctl reboot"
}

#------------------------------------------------------------------------------
# Argument parsing
#------------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --device)     shift 2 ;;   # validated + resolved by the selector above
        --target)     TARGET="$2"; shift 2 ;;
        --version)    VERSION="$2"; shift 2 ;;
        --key)        KEY="$2"; shift 2 ;;
        --rootfs)     ROOTFS_IMG="$2"; shift 2 ;;
        --boot)       BOOT_IMG="$2"; shift 2 ;;
        --hooks-tar)  HOOKS_TAR="$2"; shift 2 ;;
        --help|-h)    usage; exit 0 ;;
        *) err "Unknown option: ${1}"; usage; exit 1 ;;
    esac
done

case "${TARGET}" in
    pmos)   build_pmos ;;
    fedora) build_fedora ;;
    "")
        err "--target is required (pmos|fedora)"
        usage
        exit 1
        ;;
    *)
        err "Unknown target '${TARGET}' (expected pmos|fedora)"
        exit 1
        ;;
esac

highlight "build-ota.sh finished."
