#!/usr/bin/env bash
# =============================================================================
# phosh-phone-resolution.sh
# Forces a phone-shaped portrait resolution for Phosh in a UTM VM.
#
# Usage:
#   ./phosh-phone-resolution.sh [resolution]
#
# Resolutions:
#   390x844   (compact phone, iPhone-style)
#   414x896   (standard phone)
#   720x1280  (HD phone portrait - default)
#   custom_WxH   e.g. 1080x2340
#
# Target: aarch64 UTM VM running Phosh on Wayland
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ── Resolution Map ─────────────────────────────────────────────────────────

declare -A RESOLUTIONS
RESOLUTIONS[390x844]="390 844"
RESOLUTIONS[414x896]="414 896"
RESOLUTIONS[720x1280]="720 1280"

# ── Parse Input ───────────────────────────────────────────────────────────

RESOLUTION="${1:-720x1280}"
WIDTH="${RESOLUTION%%x*}"
HEIGHT="${RESOLUTION##*x}"

# Validate
if ! [[ "${WIDTH}" =~ ^[0-9]+$ ]] || ! [[ "${HEIGHT}" =~ ^[0-9]+$ ]]; then
    log_error "Invalid resolution: ${RESOLUTION}"
    echo "Usage: $0 [390x844|414x896|720x1280|custom_WxH]"
    exit 1
fi

if [ "${WIDTH}" -lt 200 ] || [ "${HEIGHT}" -lt 400 ]; then
    log_error "Resolution too small: ${WIDTH}x${HEIGHT}"
    exit 1
fi

log_info "Target resolution: ${WIDTH}x${HEIGHT} (portrait)"

# ── Detect Display Name ────────────────────────────────────────────────────

detect_display_name() {
    if command -v wlr-randr &>/dev/null; then
        DISPLAY_NAME=$(wlr-randr 2>/dev/null | head -1 | awk '{print $1}')
        if [ -n "${DISPLAY_NAME}" ]; then
            echo "${DISPLAY_NAME}"
            return 0
        fi
    fi

    if command -v wlrctl &>/dev/null; then
        DISPLAY_NAME=$(wlrctl output list 2>/dev/null | head -1 | awk '{print $1}')
        if [ -n "${DISPLAY_NAME}" ]; then
            echo "${DISPLAY_NAME}"
            return 0
        fi
    fi

    # Default fallback
    echo "Virtual-1"
}

# ── Configure Wayland Output ──────────────────────────────────────────────

configure_wayland_output() {
    local DISPLAY_NAME WLR_CONFIG

    DISPLAY_NAME=$(detect_display_name)
    log_info "Detected display: ${DISPLAY_NAME}"

    # Method 1: wlr-randr (preferred)
    if command -v wlr-randr &>/dev/null; then
        log_info "Configuring via wlr-randr..."
        export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
        export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"

        wlr-randr --output "${DISPLAY_NAME}" \
            --mode "${WIDTH}x${HEIGHT}" \
            --transform normal \
            2>/dev/null || {
            log_warn "wlr-randr failed — trying custom mode"
            # Try adding custom mode
            wlr-randr --output "${DISPLAY_NAME}" \
                --custom-mode "${WIDTH}x${HEIGHT}@60" \
                --transform normal \
                2>/dev/null || log_warn "wlr-randr custom mode also failed"
        }
    fi

    # Method 2: WLROOTS_CONFIG environment
    if [ -n "${DISPLAY_NAME}" ]; then
        WLR_CONFIG="${DISPLAY_NAME}:${WIDTH}x${HEIGHT}@60"
        log_info "Setting WLROOTS_CONFIG=${WLR_CONFIG}"
        export WLROOTS_CONFIG="${WLR_CONFIG}"
    fi

    # Method 3: Kernel video mode (for early boot config)
    if [ -d /sys/class/drm ]; then
        for card in /sys/class/drm/card*-*; do
            if [ -e "${card}/status" ]; then
                STATUS=$(cat "${card}/status" 2>/dev/null || echo "unknown")
                if [ "${STATUS}" = "connected" ]; then
                    CONNECTOR="${card##*/}"
                    log_info "Found DRM connector: ${CONNECTOR}"
                    echo "${WIDTH}x${HEIGHT}" > "${card}/modes" 2>/dev/null || true
                fi
            fi
        done
    fi

    log_info "Wayland output configured for ${WIDTH}x${HEIGHT}"
}

# ── Configure Phosh for Portrait ──────────────────────────────────────────

configure_phosh_portrait() {
    local PHOSH_CONFIG_DIR="${HOME:-/home/nuxel}/.config/phosh"

    mkdir -p "${PHOSH_CONFIG_DIR}"

    cat > "${PHOSH_CONFIG_DIR}/phosh.ini" << 'PHOSHEOF'
[shell]
lockdown-mode=on
show-window-preview=true
show-background=true
show-top-bar=true
max-notifications=5

[lock-screen]
show-background=true
idle-timeout-sec=60

[top-bar]
show-clock=true
show-battery=true
show-notifications=true
show-rotation-lock=true

[quick-settings]
show-wifi=true
show-bluetooth=true
show-rotation-lock=true
show-flashlight=true
show-dnd=true
rows=2
columns=4

[notifications]
do-not-disturb=false
show-on-lock-screen=true
group-by-app=true
PHOSHEOF

    log_info "Phosh configured for portrait mode"
}

# ── Configure Squeekboard for Phone Layout ────────────────────────────────

configure_squeekboard() {
    local SQUEEK_DIR="${HOME:-/home/nuxel}/.config/squeekboard"

    mkdir -p "${SQUEEK_DIR}"

    cat > "${SQUEEK_DIR}/config.ini" << 'SQUEEOF'
[keyboard]
layout=phone
show-emoji-button=true
show-clipboard-button=true
auto-capitalize=true
auto-correct=true
SQUEEOF

    log_info "Squeekboard configured for phone layout"
}

# ── Restart Phosh Session ─────────────────────────────────────────────────

restart_phosh() {
    log_info "Restarting Phosh session..."

    # Tell phosh to reload its config
    if command -v phosh &>/dev/null; then
        pkill -HUP phosh 2>/dev/null || true
    fi

    # Reload Wayland output
    if command -v wlr-randr &>/dev/null; then
        export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
        export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
        local DISPLAY_NAME
        DISPLAY_NAME=$(detect_display_name)
        wlr-randr --output "${DISPLAY_NAME}" \
            --mode "${WIDTH}x${HEIGHT}" \
            --transform normal \
            2>/dev/null || true
    fi

    log_info "Phosh session refreshed"
}

# ── Create Desktop Shortcut for Resolution Switching ──────────────────────

create_desktop_shortcut() {
    local APPS_DIR="${HOME:-/home/nuxel}/.local/share/applications"
    mkdir -p "${APPS_DIR}"

    cat > "${APPS_DIR}/nuxel-resolution-switcher.desktop" << 'DESKEOF'
[Desktop Entry]
Type=Application
Name=Nuxel Resolution Switcher
Comment=Switch between phone-shaped resolutions
Exec=/opt/nuxel/bin/phosh-phone-resolution.sh
Icon=display-symbolic
Terminal=true
Categories=Settings;System;
DESKEOF

    log_info "Desktop shortcut created"
}

# ── Main ──────────────────────────────────────────────────────────────────

main() {
    echo ""
    echo "=============================================="
    echo "  Phosh Phone Resolution Configurator"
    echo "  Resolution: ${WIDTH}x${HEIGHT}"
    echo "=============================================="
    echo ""

    if [ "$(id -u)" -eq 0 ]; then
        log_warn "Running as root — Wayland environment may need XDG_RUNTIME_DIR set"
    fi

    configure_wayland_output
    configure_phosh_portrait
    configure_squeekboard
    restart_phosh
    create_desktop_shortcut

    echo ""
    echo "=============================================="
    echo -e "${GREEN}  Resolution set to ${WIDTH}x${HEIGHT}${NC}"
    echo ""
    echo "  Presets:"
    echo "    $0 390x844   (compact phone)"
    echo "    $0 414x896   (standard phone)"
    echo "    $0 720x1280  (HD phone)"
    echo "    $0 1080x2340 (custom)"
    echo ""
    echo "  Note: If the display doesn't update, log out and back in,"
    echo "  or reboot the VM."
    echo "=============================================="
}

main "$@"
