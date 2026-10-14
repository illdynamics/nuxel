#!/usr/bin/env bash
# Shared configuration for the Nuxel Heimdall fork tooling.
#
# Overridable environment:
#   NUXEL_HEIMDALL_UPSTREAM  upstream repo (default: git.sr.ht grimler/Heimdall)
#   NUXEL_HEIMDALL_REF       upstream tag to build (default: v2.2.2)
#   NUXEL_HEIMDALL_COMMIT    expected commit for that tag (provenance check)
#   NUXEL_HEIMDALL_WORK      work/build directory
#   NUXEL_HEIMDALL_MIRROR    fallback upstream (GitHub mirror of the same tree)
set -euo pipefail

NUXEL_HEIMDALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NUXEL_REPO_ROOT="$(cd "${NUXEL_HEIMDALL_DIR}/../.." && pwd)"

NUXEL_HEIMDALL_UPSTREAM="${NUXEL_HEIMDALL_UPSTREAM:-https://git.sr.ht/~grimler/Heimdall}"
NUXEL_HEIMDALL_REF="${NUXEL_HEIMDALL_REF:-v2.2.2}"
NUXEL_HEIMDALL_COMMIT="${NUXEL_HEIMDALL_COMMIT:-d9554e7fa30a00abed7f0ac86b10e63c2c3b8e20}"
NUXEL_HEIMDALL_MIRROR="${NUXEL_HEIMDALL_MIRROR:-https://github.com/JingMatrix/Heimdall}"
NUXEL_HEIMDALL_WORK="${NUXEL_HEIMDALL_WORK:-${NUXEL_REPO_ROOT}/build/heimdall-nuxel}"
NUXEL_HEIMDALL_SRC="${NUXEL_HEIMDALL_WORK}/src"
NUXEL_HEIMDALL_OUT="${NUXEL_HEIMDALL_WORK}/out"
NUXEL_HEIMDALL_LOGS="${NUXEL_HEIMDALL_WORK}/logs"
NUXEL_HEIMDALL_PATCHES="${NUXEL_HEIMDALL_DIR}/patches"

export NUXEL_HEIMDALL_DIR NUXEL_REPO_ROOT NUXEL_HEIMDALL_WORK NUXEL_HEIMDALL_SRC
export NUXEL_HEIMDALL_OUT NUXEL_HEIMDALL_LOGS NUXEL_HEIMDALL_PATCHES

log() { echo "[heimdall-nuxel] $*"; }
err() { echo "[heimdall-nuxel][error] $*" >&2; }
