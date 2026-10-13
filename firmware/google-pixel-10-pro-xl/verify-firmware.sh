#!/usr/bin/env bash
#==============================================================================
# Nuxel firmware verifier — sha256 against firmware/manifest.yml
#
# Verifies every firmware blob listed in firmware/manifest.yml exists in the
# rootfs and that its sha256 matches the `checksum.sha256` recorded in the
# manifest. Blobs whose manifest hash is still a PLACEHOLDER are reported as
# "not-yet-verified" but do not fail the run (they become hard requirements
# only once a real hash is filled in).
#
# Usage:
#   ./firmware/verify-firmware.sh [--root <dir>] [--strict] [-v]
#
#   --root <dir>   verify against a root directory (e.g. the VM rootfs) rather
#                  than the live system. Default "/".
#   --strict       fail (non-zero) when any blob is missing OR its hash is a
#                  placeholder. Default: placeholders are warnings only.
#   -v             verbose (also list optional/auxiliary entries).
#
# Exit codes:
#   0  all checked blobs present + valid (or only-placeholder warnings when not --strict)
#   1  a non-placeholder hash mismatch
#   2  a required blob is missing
#   3  cannot read the manifest
#==============================================================================

set -uo pipefail

# Resolve the repo root whether invoked directly or via the legacy symlink
# firmware/verify-firmware.sh -> google-pixel-10-pro-xl/verify-firmware.sh.
_NUXEL_SRC="${BASH_SOURCE[0]}"
while [ -h "${_NUXEL_SRC}" ]; do
    _NUXEL_DIR="$(cd -P "$(dirname "${_NUXEL_SRC}")" && pwd)"
    _NUXEL_SRC="$(readlink "${_NUXEL_SRC}")"
    case "${_NUXEL_SRC}" in
        /*) ;;
        *) _NUXEL_SRC="${_NUXEL_DIR}/${_NUXEL_SRC}" ;;
    esac
done
NUXEL_ROOT="$(cd -P "$(dirname "${_NUXEL_SRC}")/../.." && pwd)"

# Source the shared device selector but restore our own option set afterwards:
# this verifier deliberately runs without `set -e` (it tracks errors via
# return codes), while the selector enables `set -euo pipefail` for its logic.
_NUXEL_OLD_OPTS="$(set +o)"
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
eval "${_NUXEL_OLD_OPTS}"
[ "${NUXEL_DEVICE_KEY}" = "mustang" ] || {
    echo "[verify-fw][error] firmware/${NUXEL_DEVICE_DIR}/verify-firmware.sh is ONLY for mustang. Got: ${NUXEL_DEVICE_KEY}" >&2
    exit 1
}

MANIFEST="${NUXEL_ROOT}/firmware/${NUXEL_DEVICE_DIR}/manifest.yml"
ROOT="/"
STRICT=0
VERBOSE=0

log()    { echo "[verify-fw] $*"; }
warn()   { echo "[verify-fw][warn] $*" >&2; }
err()    { echo "[verify-fw][error] $*" >&2; }

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --root) ROOT="$2"; shift 2 ;;
            --strict) STRICT=1; shift ;;
            -v|--verbose) VERBOSE=1; shift ;;
            -h|--help)
                cat <<'HELP'
Nuxel firmware verifier.
Usage: verify-firmware.sh [--root <dir>] [--strict] [-v]
HELP
                exit 0 ;;
            *) err "Unknown option: $1"; exit 1 ;;
        esac
    done
}

sha256_of() {
    # portable sha256 for macOS (shasum) and Linux (sha256sum)
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" 2>/dev/null | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    else
        return 1
    fi
}

is_placeholder() {
    local v="$1"
    case "$v" in
        ""|PLACEHOLDER*|verify_against_stock|sha256:verify*) return 0 ;;
        *) return 1 ;;
    esac
}

main() {
    parse_args "$@"

    if [ ! -f "$MANIFEST" ]; then
        err "Manifest not found: $MANIFEST"
        return 3
    fi

    # Use python3 to flatten the manifest into "dest|required|sha256" lines.
    if ! command -v python3 >/dev/null 2>&1; then
        err "python3 required to parse manifest.yml"
        return 3
    fi

    local passes=0 missing=0 mismatch=0 placeholders=0

    while IFS='|' read -r dst required sha desc; do
        [ -z "$dst" ] && continue
        local full="${ROOT%/}${dst}"
        if [ ! -f "$full" ]; then
            if [ "$required" = "true" ] || [ "$required" = "1" ]; then
                warn "MISSING required: ${dst}"
                missing=$((missing+1))
            elif [ "$VERBOSE" -eq 1 ]; then
                log "optional not present (ok): ${dst}"
            fi
            continue
        fi

        if is_placeholder "$sha"; then
            [ "$VERBOSE" -eq 1 ] && log "placeholder hash (not-yet-verified): ${dst}"
            placeholders=$((placeholders+1))
            continue
        fi

        local actual
        actual="$(sha256_of "$full")" || { err "cannot hash ${full}"; mismatch=$((mismatch+1)); continue; }
        if [ "$actual" = "$sha" ]; then
            log "OK  ${dst}"
            passes=$((passes+1))
        else
            err "HASH MISMATCH ${dst}: expected ${sha}, got ${actual}"
            mismatch=$((mismatch+1))
        fi
    done < <(MANIFEST="$MANIFEST" python3 <<'PY'
import os, yaml, sys
try:
    d = yaml.safe_load(open(os.environ['MANIFEST']))
except Exception as e:
    sys.stderr.write("manifest parse error: %s\n" % e)
    sys.exit(3)
files = d.get('firmware_files', {})
for cat, lst in files.items():
    for fw in lst if isinstance(lst, list) else []:
        dst   = fw.get('dest', '')
        req   = 'true' if fw.get('required', False) else 'false'
        cs    = fw.get('checksum', {})
        if isinstance(cs, dict):
            sha = str(cs.get('sha256', ''))
        elif isinstance(cs, str):
            # e.g. "sha256:verify_against_stock" — keep the string so the
            # is_placeholder matcher treats it as a not-yet-verified hash.
            sha = cs
        else:
            sha = ''
        desc  = fw.get('description', '')
        print(f"{dst}|{req}|{sha}|{desc}")
PY
)

    echo ""
    log "Verify summary: ${passes} ok, ${missing} missing, ${mismatch} mismatch, ${placeholders} placeholder."
    local rc=0
    if [ "$missing" -gt 0 ]; then rc=2; fi
    if [ "$mismatch" -gt 0 ]; then rc=1; fi
    if [ "${STRICT}" -eq 1 ] && [ "$placeholders" -gt 0 ]; then
        err "(--strict) ${placeholders} placeholder hashes left unfilled."
        rc=1
    fi
    if [ "$rc" -eq 0 ]; then
        log "Firmware verification passed."
    else
        warn "Firmware verification did NOT fully pass (rc=${rc})."
    fi
    return $rc
}

main "$@"
