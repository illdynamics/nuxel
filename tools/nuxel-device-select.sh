#!/usr/bin/env bash
# nuxel-device-select.sh — Resolve NUXEL_DEVICE / --device to a canonical dir.
# Usage: source tools/nuxel-device-select.sh [--device <key>]
# After sourcing, $NUXEL_DEVICE_KEY and $NUXEL_DEVICE_DIR are exported.
#
# Resolution order: CLI --device flag > NUXEL_DEVICE env var > explicit error
# (never silently guess). Aliases: s10plus|beyond2lte, g7power|ocean.
#
# This file is a shared, device-agnostic library. No device is hardcoded as
# a default; selection is explicit only. Every per-device script sources this
# file and uses ${NUXEL_DEVICE_DIR} for per-device paths.

set -euo pipefail

_nuxel_resolve_device() {
    local _key="${NUXEL_DEVICE:-}"
    # Allow --device flag override passed as positional args from the caller
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --device) _key="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    case "${_key}" in
        mustang)  NUXEL_DEVICE_DIR="google-pixel-10-pro-xl" ;;
        s10plus|beyond2lte) _key="s10plus"; NUXEL_DEVICE_DIR="s10plus" ;;
        g7power|ocean)      _key="g7power"; NUXEL_DEVICE_DIR="g7power" ;;
        "") echo "ERROR: NUXEL_DEVICE is not set and --device was not passed." >&2
            echo "       Valid values: mustang, s10plus, g7power" >&2
            exit 1 ;;
        *) echo "ERROR: Unknown device key '${_key}'." >&2
           echo "       Valid values: mustang, s10plus, g7power" >&2
           exit 1 ;;
    esac
    export NUXEL_DEVICE_KEY="${_key}"
    export NUXEL_DEVICE_DIR
    echo "[nuxel] Device key:       ${NUXEL_DEVICE_KEY}"
    echo "[nuxel] Device directory: ${NUXEL_DEVICE_DIR}"
}
_nuxel_resolve_device "$@"
