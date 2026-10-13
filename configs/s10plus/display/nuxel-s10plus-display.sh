#!/usr/bin/env bash
#==============================================================================
# Nuxel S10+ display bring-up — Samsung Galaxy S10+ (beyond2lte)
#
# Sets the Samsung S6E3HA9 Dynamic AMOLED panel (3040x1440, 19:9, HDR10+,
# DDIC s6e3ha9_beyond2) to its native portrait scanout mode via wlr-randr on
# the running Wayland/Phosh session. Runs AFTER the compositor owns outputs.
#
# Behaviour:
#   * Resolves the device through tools/nuxel-device-select.sh (CLI --device
#     flag > NUXEL_DEVICE env > explicit error; never silently guessed) and
#     refuses to run for any key other than s10plus (this is a device-specific
#     artifact under configs/s10plus/).
#   * Reads NUXEL_DISPLAY_RESOLUTION / NUXEL_DISPLAY_DDIC from the device conf
#     conventions (device/s10plus/nuxel-beyond2lte.conf), if present.
#   * Applies `wlr-randr --output DSI-1 --mode 1440x3040` (portrait scanout of
#     the 3040x1440 panel spec). Fails gracefully with a WARN (non-fatal):
#     on the UTM VM there is no S6E3HA9 panel, and on real hardware the
#     display node may simply not be up yet.
#
# Install on the S10+ target:
#   install -m0755 configs/s10plus/display/nuxel-s10plus-display.sh \
#       /usr/local/bin/nuxel-s10plus-display
#   # autostart with Phosh: ~/.config/autostart/nuxel-s10plus-display.desktop
#   # or an OpenRC "local" hook on the pmOS target.
#==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NUXEL_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

log()  { echo "[nuxel-s10plus-display] $*"; }
warn() { echo "[nuxel-s10plus-display][warn] $*" >&2; }
die()  { echo "[nuxel-s10plus-display][error] $*" >&2; exit 1; }

usage() {
    cat <<'EOF'
Usage: nuxel-s10plus-display.sh [--device s10plus] [--output <connector>]

Sets the S6E3HA9 AMOLED panel to its native 3040x1440 (portrait scanout
1440x3040) mode on the given wlr-randr output.

Options:
  --device <key>   Device key (s10plus|beyond2lte). Defaults to NUXEL_DEVICE.
  --output <name>  wlr-randr connector name (default: ${NUXEL_DISPLAY_OUTPUT:-DSI-1}).
  -h, --help       Show this help and exit.
EOF
}

# --- Parse CLI (pass --device through to the shared selector) ----------------
DEVICE_ARGS=()
OUTPUT="${NUXEL_DISPLAY_OUTPUT:-DSI-1}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --device) DEVICE_ARGS+=(--device "$2"); shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1";;
    esac
done

# --- Resolve the device through the shared selector --------------------------
# shellcheck source=../../../tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "${DEVICE_ARGS[@]}"

# This script is device-specific: refuse to run for any other key.
[[ "${NUXEL_DEVICE_KEY}" == "s10plus" ]] || \
    die "configs/s10plus display script refuses device key '${NUXEL_DEVICE_KEY}' (expected s10plus)."

# --- Load device conf conventions (device/s10plus/nuxel-beyond2lte.conf) -----
# The conf is a plain shell fragment exporting NUXEL_DISPLAY_RESOLUTION and
# NUXEL_DISPLAY_DDIC (among others). Load it when present; environment values
# already exported by the init environment take precedence only via the
# defaults applied below — the conf itself is the operator's stub to fill.
CONF_FILE="${NUXEL_ROOT}/device/${NUXEL_DEVICE_DIR}/nuxel-beyond2lte.conf"
if [[ -r "${CONF_FILE}" ]]; then
    # shellcheck source=/dev/null
    source "${CONF_FILE}"
    log "Loaded device conf: ${CONF_FILE}"
else
    warn "Device conf not found (${CONF_FILE}); using defaults."
fi

NUXEL_DISPLAY_RESOLUTION="${NUXEL_DISPLAY_RESOLUTION:-3040x1440}"
NUXEL_DISPLAY_DDIC="${NUXEL_DISPLAY_DDIC:-S6E3HA9}"

# --- Derive the wlr-randr scanout mode ---------------------------------------
# NUXEL_DISPLAY_RESOLUTION is the panel spec in "long-edge x short-edge" order
# (3040x1440). wlr-randr modes are "WIDTH x HEIGHT" of the scanout, so the
# portrait framebuffer is 1440 wide x 3040 tall.
DISPLAY_W=1440
DISPLAY_H=3040
if [[ "${NUXEL_DISPLAY_RESOLUTION}" =~ ^([0-9]+)x([0-9]+)$ ]]; then
    _res_long="${BASH_REMATCH[1]}"
    _res_short="${BASH_REMATCH[2]}"
    if (( _res_long >= _res_short )); then
        DISPLAY_W="${_res_short}"
        DISPLAY_H="${_res_long}"
    else
        DISPLAY_W="${_res_long}"
        DISPLAY_H="${_res_short}"
    fi
fi
MODE="${DISPLAY_W}x${DISPLAY_H}"

# --- Apply the mode (graceful, non-fatal) -------------------------------------
log "Setting ${NUXEL_DISPLAY_RESOLUTION} panel (${NUXEL_DISPLAY_DDIC} AMOLED, beyond2lte) to ${MODE} on ${OUTPUT}"

if ! command -v wlr-randr >/dev/null 2>&1; then
    warn "wlr-randr not found — no Wayland/Phosh session (VM?). Display setup skipped."
    exit 0
fi

if ! wlr-randr --output "${OUTPUT}" --mode "${MODE}"; then
    warn "wlr-randr failed for ${OUTPUT} — display node may not be ready yet."
    warn "Verify: ls /sys/class/drm/ (look for a Samsung S6E3HA9 panel connector)."
    warn "List available modes with: wlr-randr"
    exit 0   # graceful WARN, non-fatal
fi

log "Display mode applied: ${OUTPUT} @ ${MODE}"
