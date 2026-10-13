#!/usr/bin/env bash
#==============================================================================
# Nuxel display bring-up script — Google mustang (Pixel 10 Pro XL)
#
# Runs AFTER Phosh / the Wayland compositor starts on mustang. It:
#   1. Sets the Samsung AMB655X LTPO panel to its native 1440x3120@120Hz mode
#      (via DRM / wlr-randr when wlroots, else via xrandr/Wayland).
#   2. Applies the touch rotation calibration matrix to libinput.
#   3. Backs off gracefully on the VM (no AMB655X panel) so the same script can
#      be exercised in the UTM/Fedora image without failing.
#
# Install on mustang (systemctl user / OpenRC local):
#   install -m0755 configs/display/nuxel-mustang-start.sh \
#       /usr/local/bin/nuxel-mustang-start
#   # Phosh / lid-close-like autostart entry:
#   mkdir -p ~/.config/autostart
#   cp shell/config/systemd-user/nuxel-home-kiosk.service ~/.config/systemd/user/ 2>/dev/null
#   # or add an OpenRC "local" hook on the pmOS target.
#==============================================================================

set -euo pipefail

log() { echo "[nuxel-mustang-start] $*"; }
warn() { echo "[nuxel-mustang-start][warn] $*" >&2; }

PANEL_NAME="AMB655X-1"   # wlr-randr / DRM connector name discovered at runtime
NATIVE_MODE="1440x3120"
NATIVE_RATE=120

# --- 1. Determine a usable output tool ----------------------------------------
OUTPUT_TOOL=""
if command -v wlr-randr >/dev/null 2>&1; then
    OUTPUT_TOOL="wlr-randr"
elif command -v kanshi >/dev/null 2>&1; then
    OUTPUT_TOOL="kanshi"
elif command -v xrandr >/dev/null 2>&1; then
    OUTPUT_TOOL="xrandr"
fi

apply_panel_mode() {
    local head="${1:-$PANEL_NAME}"

    case "${OUTPUT_TOOL}" in
        wlr-randr)
            # Generic wlroots: try the AMB655X connector, fall back to first output.
            local conn
            conn="$(wlr-randr --json 2>/dev/null | python3 -c "import sys,json;
try:
    d=json.load(sys.stdin); outs=d if isinstance(d,list) else d.get('outputs',[])
    for o in outs:
        n=o.get('name','')
        if 'AMB' in n or 'DSI' in n or 'eDP' in n: print(n); break
    else: print(outs[0]['name'] if outs else '')
except Exception: print('')" || true)"
            [ -z "${conn}" ] && conn="${head}"
            log "wlr-randr: setting ${conn} to ${NATIVE_MODE}@${NATIVE_RATE}Hz"
            wlr-randr --output "${conn}" --mode "${NATIVE_MODE}" --rate "${NATIVE_RATE}" \
                || wlr-randr --output "${conn}" --mode "${NATIVE_MODE}" \
                || warn "wlr-randr could not apply ${NATIVE_MODE}@${NATIVE_RATE}"
            ;;
        kanshi)
            # kanshi applies a profile; we just reload to trigger it.
            log "kanshi: reloading profiles for ${NATIVE_MODE}@${NATIVE_RATE}"
            killall -SIGHUP kanshi 2>/dev/null || true
            ;;
        xrandr)
            xrandr --output "${head}" --mode "${NATIVE_MODE}" --rate "${NATIVE_RATE}" \
                || xrandr --output "${head}" --mode "${NATIVE_MODE}" \
                || warn "xrandr could not apply mode"
            ;;
        "")
            warn "No randr tool found; skipping panel mode (VM-backoff)."
            ;;
    esac
}

# --- 2. Apply touch rotation calibration matrix -------------------------------
apply_touch_matrix() {
    # Cartesian rotation for portrait-native AMB655X. When the framebuffer /
    # output coordinate system needs the touch input rotated 90° CCW the
    # canonical libinput calibration matrix is:
    #   0 -1 1
    #   1  0 0
    #   0  0 1   (swap X/Y to match portrait panel orientation)
    #
    # The matrix is applied persistently via the libinput override file
    # configs/libinput/nuxel-mustang-touch.conf; we only nudge it at runtime via
    # xinput if available (Wayland libinput does not allow live override).
    if command -v xinput >/dev/null 2>&1 && xinput list >/dev/null 2>&1; then
        local dev
        dev="$(xinput list --name-only | grep -iE 's6sy791|mustang-touch|goodix' | head -1 || true)"
        if [ -n "${dev}" ]; then
            log "Applying touch rotation matrix to '${dev}'"
            xinput set-prop "${dev}" 'libinput Calibration Matrix' 0 -1 1 1 0 0 0 0 1 \
                || warn "xinput could not apply calibration matrix"
        fi
    else
        log "No X input device; touch matrix applied via libinput conf (Wayland)."
    fi
}

# --- 3. Device detection --------------------------------------------------------
# Real mustang panel : wlr-randr reports a connector whose EDID/model matches
# "AMB655X". VM / UTM : no such connector, we back off cleanly.
has_mustang_panel() {
    if command -v wlr-randr >/dev/null 2>&1; then
        if wlr-randr --json 2>/dev/null | grep -qiE 'AMB|655X|Samsung'; then
            return 0
        fi
        return 1
    fi
    # Fallback: check sysfs DRM panel bits.
    if grep -rqiE 'AMB655X|6539' /sys/class/drm/*/device/.* 2>/dev/null; then
        return 0
    fi
    return 1
}

main() {
    log "Nuxel mustang display bring-up starting"

    # Wait briefly for the compositor to own the outputs.
    sleep 2

    if has_mustang_panel; then
        apply_panel_mode
        apply_touch_matrix
        log "Display setup applied (module ${PANEL_NAME})."
    else
        log "No AMB655X panel detected (VM/other) — display setup skipped (graceful)."
    fi

    log "Nuxel mustang display bring-up complete"
}

main "$@"
