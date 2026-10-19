#!/usr/bin/env bash
# Apply the Nuxel instrumentation patches to a pristine upstream tree.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

[ -d "${NUXEL_HEIMDALL_SRC}/.git" ] || { err "run fetch-upstream.sh first"; exit 1; }

git -C "${NUXEL_HEIMDALL_SRC}" reset --hard --quiet
git -C "${NUXEL_HEIMDALL_SRC}" clean -fd --quiet

shopt -s nullglob
patches=("${NUXEL_HEIMDALL_PATCHES}"/*.patch)
shopt -u nullglob

[ "${#patches[@]}" -gt 0 ] || { err "no patches in ${NUXEL_HEIMDALL_PATCHES}"; exit 1; }

for patch in "${patches[@]}"; do
    log "applying $(basename "${patch}")"
    git -C "${NUXEL_HEIMDALL_SRC}" apply --whitespace=nowarn "${patch}"
done

log "applied ${#patches[@]} patch(es)"
