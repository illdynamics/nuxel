#!/usr/bin/env bash
# Build the Nuxel-instrumented Heimdall CLI on Fedora 43 (aarch64 or x86_64).
#
# Requirements:
#   sudo dnf install -y gcc-c++ cmake make pkgconf-pkg-config libusb1-devel git
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

DIR="$(dirname "${BASH_SOURCE[0]}")"

if [ "$(uname -s)" != "Linux" ]; then
    err "this script is for Fedora/Linux; use build-macos-apple-silicon.sh on macOS"
    exit 1
fi

if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    log "distribution: ${PRETTY_NAME:-unknown}"
fi

missing=0
for tool in cmake git pkg-config c++; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        err "missing '${tool}'"
        missing=1
    fi
done
if ! pkg-config --exists libusb-1.0 2>/dev/null; then
    err "libusb-1.0 development files not found"
    missing=1
fi

if [ "${missing}" -ne 0 ]; then
    err "install the build dependencies:"
    err "  sudo dnf install -y gcc-c++ cmake make pkgconf-pkg-config libusb1-devel git"
    exit 1
fi

log "libusb: $(pkg-config --modversion libusb-1.0), arch: $(uname -m)"

bash "${DIR}/fetch-upstream.sh"
bash "${DIR}/apply-patches.sh"

BUILD_DIR="${NUXEL_HEIMDALL_WORK}/build-fedora"
mkdir -p "${BUILD_DIR}" "${NUXEL_HEIMDALL_OUT}"

cmake -S "${NUXEL_HEIMDALL_SRC}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=Release -DDISABLE_FRONTEND=true
cmake --build "${BUILD_DIR}" --parallel "$(nproc)"

cp "${BUILD_DIR}/bin/heimdall" "${NUXEL_HEIMDALL_OUT}/heimdall-nuxel"
chmod +x "${NUXEL_HEIMDALL_OUT}/heimdall-nuxel"

log "built: ${NUXEL_HEIMDALL_OUT}/heimdall-nuxel"
"${NUXEL_HEIMDALL_OUT}/heimdall-nuxel" version

cat <<'NOTE'

Fedora 43 udev note (needed to access Download Mode without root):
  sudo tee /etc/udev/rules.d/60-heimdall.rules >/dev/null <<'RULE'
  SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", MODE="0666"
  SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", ATTR{idProduct}=="685d", TAG+="uaccess"
  RULE
  sudo udevadm control --reload-rules && sudo udevadm trigger
NOTE
