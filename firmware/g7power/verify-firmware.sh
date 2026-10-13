#!/usr/bin/env bash
#==============================================================================
# Nuxel G7 Power firmware verifier — sha256 against firmware/g7power/manifest.yml
#
# Self-contained verifier for the Motorola Moto G7 Power (g7power, ocean)
# manifest. It NEVER references the mustang or s10plus manifests or paths.
#
# Rules (per the G7 Power manifest semantics):
#   - required:true  blobs are either "verified" (real sha256 present in the
#                    manifest AND matching the installed blob) or "pending"
#                    (manifest checksum is still UNKNOWN/PLACEHOLDER). Pending
#                    blobs do NOT fail the run — they are a reminder that
#                    Phase 0 inventory has not been collected yet.
#   - required:false blobs are advisory only.
#
# Device guard: explicit selection required (NUXEL_DEVICE=g7power or
# --device g7power); aborts for any other device key. The G7 Power uses stock
# ABOOT + lk2nd fastboot (no fastbootd/vendor_boot/init_boot/vbmeta). This
# script never writes to any device partition, and never touches the
# protected partitions modemst1 modemst2 fsg fsc ddr persist misc.
#
# Usage:
#   NUXEL_DEVICE=g7power firmware/g7power/verify-firmware.sh [--root <dir>] [--strict] [-v]
#   firmware/g7power/verify-firmware.sh --device g7power --root <dir> --strict
#
#   --root <dir>   verify against a root directory (e.g. the rootfs staging)
#                  rather than the live system. Default "/".
#   --strict       fail (non-zero) when any required blob is missing OR its
#                  checksum is still a placeholder. Default: placeholders are
#                  pending warnings only.
#   -v             verbose (also list optional/advisory entries).
#
# Exit codes:
#   0  all checked blobs present + valid (pending/UNKNOWN checksums allowed
#      unless --strict)
#   1  a non-placeholder hash mismatch (or --strict with pending entries)
#   2  a required blob is missing
#   3  cannot read the manifest / missing python3+PyYAML
#
# The G7 Power never flashes modemst1/modemst2/fsg/fsc/ddr/persist/misc —
# they hold per-unit IMEI/MAC/radio calibration and are irreplaceable.
#==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="${SCRIPT_DIR}/manifest.yml"
ROOT="/"
STRICT=0
VERBOSE=0

log()  { echo "[verify-fw-g7power] $*"; }
warn() { echo "[verify-fw-g7power][warn] $*" >&2; }
err()  { echo "[verify-fw-g7power][error] $*" >&2; }

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --device) [ -n "${2:-}" ] || { err "--device requires a value"; exit 1; }
                # shellcheck disable=SC2034 # consumed by tools/nuxel-device-select.sh via env
                NUXEL_DEVICE="$2"; shift 2 ;;
            --root) ROOT="$2"; shift 2 ;;
            --strict) STRICT=1; shift ;;
            -v|--verbose) VERBOSE=1; shift ;;
            -h|--help)
                sed -n '2,42p' "$0" | sed 's/^# \{0,1\}//'
                exit 0 ;;
            *) err "Unknown option: $1"; exit 1 ;;
        esac
    done
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" 2>/dev/null | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    else
        return 1
    fi
}

is_pending() {
    local v="$1"
    case "$v" in
        ""|UNKNOWN*|PLACEHOLDER*|TBD*|sha256:verify*) return 0 ;;
        *) return 1 ;;
    esac
}

main() {
    parse_args "$@"

    # Device guard — g7power only. Explicit selection required (env or --device).
    NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
    # shellcheck source=tools/nuxel-device-select.sh
    source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
    [ "${NUXEL_DEVICE_KEY}" = "g7power" ] || {
        err "This verifier is ONLY for the Motorola Moto G7 Power (g7power). Got: ${NUXEL_DEVICE_KEY}"
        return 1
    }

    [ -f "$MANIFEST" ] || { err "Manifest not found: $MANIFEST"; return 3; }
    command -v python3 >/dev/null 2>&1 || { err "python3 required to parse manifest.yml"; return 3; }
    if ! python3 -c 'import yaml' 2>/dev/null; then
        err "PyYAML required to parse manifest.yml"; return 3
    fi

    # Fail closed: the verification loop consumes the manifest via a process
    # substitution whose python3 exit status is masked, so an unparseable
    # manifest would otherwise be read as empty and falsely report "passed".
    # Validate the YAML up front and return 3 (manifest/python3/PyYAML
    # problem) on parse failure.
    if ! python3 -c 'import yaml,sys; yaml.safe_load(open(sys.argv[1], encoding="utf-8"))' "$MANIFEST"; then
        err "Manifest parse error (python3/PyYAML): $MANIFEST — refusing to verify."
        return 3
    fi

    local passes=0 missing=0 mismatch=0 pending=0 advisory=0

    while IFS='|' read -r dst required sha _desc; do
        [ -z "$dst" ] && continue
        if [ "$required" = "false" ]; then
            advisory=$((advisory+1))
            [ "$VERBOSE" -eq 1 ] && log "advisory (ok): ${dst}"
            continue
        fi

        local full="${ROOT%/}${dst}"
        if [ ! -f "$full" ]; then
            if is_pending "$sha"; then
                warn "MISSING (pending, checksum UNKNOWN): ${dst}"
                pending=$((pending+1))
            else
                warn "MISSING required: ${dst}"
                missing=$((missing+1))
            fi
            continue
        fi

        if is_pending "$sha"; then
            log "PENDING (checksum UNKNOWN): ${dst}"
            pending=$((pending+1))
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
    d = yaml.safe_load(open(os.environ['MANIFEST'], encoding='utf-8'))
except Exception as e:
    sys.stderr.write("manifest parse error: %s\n" % e)
    sys.exit(3)
for cat, lst in d.get('firmware_files', {}).items():
    for fw in lst if isinstance(lst, list) else []:
        dst  = str(fw.get('dest', ''))
        req  = 'true' if fw.get('required', False) else 'false'
        cs   = fw.get('checksum', '')
        if isinstance(cs, dict):
            sha = str(cs.get('sha256', ''))
        else:
            sha = str(cs)
        print(f"{dst}|{req}|{sha}|{str(fw.get('description',''))}")
PY
)

    echo ""
    log "Verify summary: ${passes} ok, ${missing} missing, ${mismatch} mismatch, ${pending} pending (UNKNOWN checksum), ${advisory} advisory."
    local rc=0
    if [ "$missing" -gt 0 ]; then rc=2; fi
    if [ "$mismatch" -gt 0 ]; then rc=1; fi
    if [ "${STRICT}" -eq 1 ] && [ "$pending" -gt 0 ]; then
        err "(--strict) ${pending} required blob(s) still have UNKNOWN checksums — run Phase 0 inventory."
        rc=1
    fi
    if [ "$rc" -eq 0 ]; then
        log "Firmware verification passed (pending UNKNOWN checksums are expected pre-Phase-0)."
    else
        warn "Firmware verification did NOT fully pass (rc=${rc})."
    fi
    return $rc
}

main "$@"
