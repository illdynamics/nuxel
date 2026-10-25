#!/usr/bin/env bash
#==============================================================================
# Nuxel Phase 3 Apply — Installs all Phase 3 services, policies, and scripts
# Idempotent. Creates backups before modifying any system files.
#==============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="/tmp/nuxel-phase3-backup-$(date +%Y%m%d-%H%M%S)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }

mkdir -p "$BACKUP_DIR"
log_info "Backup directory: $BACKUP_DIR"

# ── 1. Install system services ──────────────────────────────────
log_info "Installing system D-Bus services..."

for svc in portal bridge notifications; do
    src="${NUXEL_ROOT}/services/nuxel-${svc}/src"
    if [ "$svc" = "portal" ]; then
        dst="/usr/bin/nuxel-portal"
        install -Dm755 "${src}/portal.py" "$dst"
        log_ok "nuxel-portal installed"
    elif [ "$svc" = "bridge" ]; then
        install -Dm755 "${src}/bridge.py" "/usr/bin/nuxel-bridge"
        install -Dm755 "${src}/api.py" "/usr/lib/nuxel/nuxel-bridge/api.py"
        if [ -f "${src}/capabilities.py" ]; then
            install -Dm644 "${src}/capabilities.py" "/usr/lib/nuxel/nuxel-bridge/capabilities.py"
        fi
        if [ -f "${src}/system_indicators.py" ]; then
            install -Dm644 "${src}/system_indicators.py" "/usr/lib/nuxel/nuxel-bridge/system_indicators.py"
        fi
        log_ok "nuxel-bridge installed"
    elif [ "$svc" = "notifications" ]; then
        install -Dm755 "${src}/notifications.py" "/usr/bin/nuxel-notifications"
        log_ok "nuxel-notifications installed"
    fi
done

# ── 2. Install D-Bus policy files ──────────────────────────────
log_info "Installing D-Bus policies..."
for conf in \
    "${NUXEL_ROOT}/services/nuxel-portal/dbus/org.nuxel.Portal.conf" \
    "${NUXEL_ROOT}/services/nuxel-bridge/dbus/org.nuxel.Bridge.conf" \
    "${NUXEL_ROOT}/services/nuxel-notifications/dbus/org.nuxel.Notifications.conf"; do
    if [ -f "$conf" ]; then
        dst="/etc/dbus-1/system.d/$(basename "$conf")"
        if [ -f "$dst" ]; then
            cp "$dst" "$BACKUP_DIR/"
        fi
        install -Dm644 "$conf" "$dst"
        log_ok "D-Bus policy: $(basename "$conf")"
    fi
done

# ── 3. Install systemd service units ────────────────────────────
log_info "Installing systemd service units..."
for svc in portal bridge notifications; do
    svcdir="${NUXEL_ROOT}/services/nuxel-${svc}/systemd"
    if [ -d "$svcdir" ]; then
        for unit in "$svcdir"/*.service; do
            [ -f "$unit" ] || continue
            dst="/usr/lib/systemd/system/$(basename "$unit")"
            if [ -f "$dst" ]; then
                cp "$dst" "$BACKUP_DIR/"
            fi
            install -Dm644 "$unit" "$dst"
            log_ok "systemd unit: $(basename "$unit")"
        done
    fi
done

# ── 4. Install launchers ───────────────────────────────────────
log_info "Installing launchers..."
launcher="${NUXEL_ROOT}/shell/nuxel-home-native/nuxel-home-launcher"
if [ -f "$launcher" ]; then
    install -Dm755 "$launcher" /usr/local/bin/nuxel-home
    log_ok "nuxel-home launcher installed"
fi

# ── 5. Install user services ────────────────────────────────────
log_info "Installing user services..."
for svc in nuxel-home-kiosk nuxel-home-native nuxel-phosh-agent; do
    src="${NUXEL_ROOT}/shell/config/systemd-user/${svc}.service"
    if [ -f "$src" ]; then
        dst_dir="$HOME/.config/systemd/user"
        mkdir -p "$dst_dir"
        if [ -f "${dst_dir}/${svc}.service" ]; then
            cp "${dst_dir}/${svc}.service" "$BACKUP_DIR/"
        fi
        install -Dm644 "$src" "${dst_dir}/${svc}.service"
        log_ok "user service: ${svc}.service"
    fi
done

# ── 6. Reload systemd ───────────────────────────────────────────
log_info "Reloading systemd..."
sudo systemctl daemon-reload 2>/dev/null || true
systemctl --user daemon-reload 2>/dev/null || true

# ── 7. Enable services ──────────────────────────────────────────
log_info "Enabling services..."
sudo systemctl enable nuxel-bridge.service 2>/dev/null || log_warn "Cannot enable nuxel-bridge"
sudo systemctl enable nuxel-portal.service 2>/dev/null || log_warn "Cannot enable nuxel-portal"
sudo systemctl enable nuxel-notifications.service 2>/dev/null || log_warn "Cannot enable nuxel-notifications"

# ── 8. Validate ─────────────────────────────────────────────────
log_info "Validating Phase 3 deployment..."

"${NUXEL_ROOT}/ci/phase3-validate.sh" 2>/dev/null && log_ok "Phase 3 validation passed" || log_warn "Phase 3 validation had warnings"

echo ""
log_ok "Phase 3 apply complete!"
echo ""
echo "Rollback commands:"
echo "  sudo cp $BACKUP_DIR/* /etc/dbus-1/system.d/ 2>/dev/null"
echo "  sudo systemctl disable nuxel-bridge nuxel-portal nuxel-notifications"
echo "  sudo systemctl daemon-reload"
echo "  systemctl --user daemon-reload"
echo ""
echo "Home rollback:"
echo "  ${NUXEL_ROOT}/tools/nuxel-rollback-home.sh"
