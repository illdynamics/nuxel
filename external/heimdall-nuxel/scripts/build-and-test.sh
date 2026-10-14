#!/usr/bin/env bash
# One-shot: fetch pristine v2.2.2, apply Nuxel patches, build the CLI, run tests.
#
# Usage:
#   external/heimdall-nuxel/scripts/build-and-test.sh
#
# macOS:   brew install cmake libusb pkgconf
# Fedora:  sudo dnf install -y gcc-c++ cmake make pkgconf-pkg-config libusb1-devel git
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

DIR="$(dirname "${BASH_SOURCE[0]}")"

bash "${DIR}/fetch-upstream.sh"
bash "${DIR}/apply-patches.sh"

if [ "$(uname -s)" = "Darwin" ]; then
    bash "${DIR}/build-macos-apple-silicon.sh"
else
    bash "${DIR}/build-fedora43.sh"
fi

# Tests must run against the same patched tree that produced the binary.
bash "${DIR}/run-tests.sh"

log "artifacts:"
log "  binary: ${NUXEL_HEIMDALL_OUT}/heimdall-nuxel"
log "  logs:   ${NUXEL_HEIMDALL_LOGS}"
