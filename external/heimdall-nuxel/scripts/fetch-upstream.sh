#!/usr/bin/env bash
# Fetch (or reset) the pristine upstream Heimdall v2.2.2 source tree.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

mkdir -p "${NUXEL_HEIMDALL_WORK}" "${NUXEL_HEIMDALL_LOGS}"

if [ -d "${NUXEL_HEIMDALL_SRC}/.git" ]; then
    git -C "${NUXEL_HEIMDALL_SRC}" fetch --quiet --tags origin || {
        err "fetch failed; falling back to the GitHub mirror"
        git -C "${NUXEL_HEIMDALL_SRC}" remote set-url origin "${NUXEL_HEIMDALL_MIRROR}"
        git -C "${NUXEL_HEIMDALL_SRC}" fetch --quiet --tags origin
    }
else
    log "cloning ${NUXEL_HEIMDALL_UPSTREAM} (fallback: ${NUXEL_HEIMDALL_MIRROR})"
    if ! git clone --quiet "${NUXEL_HEIMDALL_UPSTREAM}" "${NUXEL_HEIMDALL_SRC}"; then
        git clone --quiet "${NUXEL_HEIMDALL_MIRROR}" "${NUXEL_HEIMDALL_SRC}"
    fi
fi

git -C "${NUXEL_HEIMDALL_SRC}" checkout --quiet --force "${NUXEL_HEIMDALL_REF}"
git -C "${NUXEL_HEIMDALL_SRC}" reset --hard --quiet

actual="$(git -C "${NUXEL_HEIMDALL_SRC}" rev-parse HEAD)"
if [ "${actual}" != "${NUXEL_HEIMDALL_COMMIT}" ]; then
    err "ref ${NUXEL_HEIMDALL_REF} is ${actual}, expected ${NUXEL_HEIMDALL_COMMIT}"
    err "refusing to build an unexpected upstream revision"
    exit 1
fi

log "upstream ${NUXEL_HEIMDALL_REF} verified at ${actual}"
