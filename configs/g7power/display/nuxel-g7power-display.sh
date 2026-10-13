#!/usr/bin/env bash
#==============================================================================
# Nuxel G7 Power display bring-up — Motorola Moto G7 Power (ocean, XT1955)
#
# Sets the 6.2" IPS LCD panel (1520x720, 19:9, TI LM3697 backlight) to its
# native portrait scanout mode via wlr-randr on the running Wayland/Phosh
# session. Runs AFTER the compositor owns outputs.
#
# Behaviour:
#   * Applies `wlr-randr --output ${OUTPUT} --mode 720x1520` (portrait
#     scanout of the 1520x720 panel spec). OUTPUT defaults to DSI-1 and can
#     be overridden with NUXEL_DISPLAY_OUTPUT — the real connector name must
#     be verified on device (`wlr-randr` / `ls /sys/class/drm/`).
#   * Fails gracefully with a WARN (non-fatal, exit 0), mirroring the s10plus
#     display script convention: on the UTM VM there is no msm8953 panel, and
#     on real hardware the display node may simply not be up yet.
#
# Install on the G7 Power target:
#   install -m0755 configs/g7power/display/nuxel-g7power-display.sh \
#       /usr/local/bin/nuxel-g7power-display
#   # autostart with Phosh: ~/.config/autostart/nuxel-g7power-display.desktop
#   # or an OpenRC "local" hook on the pmOS target.
#==============================================================================

set -euo pipefail

# Set 1520x720 display mode for G7 Power IPS LCD via MSM DRM
DISPLAY_W=720
DISPLAY_H=1520
OUTPUT="${NUXEL_DISPLAY_OUTPUT:-DSI-1}"

echo "[display] Setting ${DISPLAY_W}x${DISPLAY_H} on ${OUTPUT} (IPS LCD 1520x720, LM3697 backlight)"

# Graceful, non-fatal (s10plus convention): on the UTM VM there is no
# wlr-randr / Wayland session at all, and on real hardware the display node
# may simply not be up yet. Neither case should fail a bring-up script run.
if ! command -v wlr-randr >/dev/null 2>&1; then
    echo "[display] WARN: wlr-randr not found — no Wayland/Phosh session (VM?). Display setup skipped."
    exit 0
fi

wlr-randr --output "${OUTPUT}" --mode "${DISPLAY_W}x${DISPLAY_H}" || {
    echo "[display] WARN: wlr-randr failed. Verify MSM DRM + panel is initialised."
    echo "[display] Check: ls /sys/class/drm/ | grep card"
    exit 0   # graceful WARN, non-fatal
}
