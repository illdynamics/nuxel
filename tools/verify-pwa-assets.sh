#!/usr/bin/env bash
# =============================================================================
# tools/verify-pwa-assets.sh
#
# CI assertion for the single-source assets invariant (briq-as1).
#
# Fails (non-zero exit) if ANY of the 6 PWA asset dirs does NOT byte-match the
# canonical asset:
#   assets/nuxel-background.png          -> pwa/nuxel-home/assets + 5 apps
#   assets/nuxel-boot-animation.mp4      -> pwa/nuxel-home/assets + 5 apps
#
# It also fails if a stray duplicate of the shared media is present anywhere
# else in the repo (i.e. a copy that should have been removed by git-ignoring
# the destination asset dirs and regenerating them at build time).
#
# This is intended to be wired into the CI gate (e.g. ci/validate-build.sh)
# and/or the build pipeline. It delegates to tools/dedupe-assets.sh --verify so
# there is a single source of truth for the destination list.
#
# Usage:
#   tools/verify-pwa-assets.sh
#   tools/verify-pwa-assets.sh --quiet   # only print on failure
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEDUPE="${REPO_ROOT}/tools/dedupe-assets.sh"

if [ ! -x "${DEDUPE}" ]; then
    echo "[verify-pwa-assets] ERROR: ${DEDUPE} not executable/found" >&2
    exit 1
fi

if [ "${1:-}" = "--quiet" ]; then
    # Quiet mode: only emit output when the invariant is broken.
    if ! "${DEDUPE}" --verify >/dev/null 2>&1; then
        "${DEDUPE}" --verify
        exit 1
    fi
    echo "[verify-pwa-assets] OK: all PWA asset copies match the canonical assets/ tree."
    exit 0
fi

exec "${DEDUPE}" --verify
