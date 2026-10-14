#!/usr/bin/env bash
# Build the Nuxel-instrumented Heimdall CLI on macOS (Apple Silicon or Intel).
#
# Requirements (Homebrew):
#   brew install cmake libusb pkgconf
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

DIR="$(dirname "${BASH_SOURCE[0]}")"

if [ "$(uname -s)" != "Darwin" ]; then
    err "this script is for macOS; use build-fedora43.sh on Linux"
    exit 1
fi

for tool in cmake git; do
    command -v "${tool}" >/dev/null 2>&1 || { err "missing '${tool}' (brew install cmake git)"; exit 1; }
done

if ! command -v pkg-config >/dev/null 2>&1 || ! pkg-config --exists libusb-1.0 2>/dev/null; then
    err "libusb-1.0 development files not found."
    err "install them with:  brew install libusb pkgconf"
    exit 1
fi

log "libusb: $(pkg-config --modversion libusb-1.0), arch: $(uname -m)"

bash "${DIR}/fetch-upstream.sh"
bash "${DIR}/apply-patches.sh"

BUILD_DIR="${NUXEL_HEIMDALL_WORK}/build-macos"
mkdir -p "${BUILD_DIR}" "${NUXEL_HEIMDALL_OUT}"

cmake -S "${NUXEL_HEIMDALL_SRC}" -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=Release -DDISABLE_FRONTEND=true
cmake --build "${BUILD_DIR}" --parallel "$(sysctl -n hw.ncpu)"

cp "${BUILD_DIR}/bin/heimdall" "${NUXEL_HEIMDALL_OUT}/heimdall-nuxel"
chmod +x "${NUXEL_HEIMDALL_OUT}/heimdall-nuxel"

log "built: ${NUXEL_HEIMDALL_OUT}/heimdall-nuxel"
"${NUXEL_HEIMDALL_OUT}/heimdall-nuxel" version
