#!/usr/bin/env bash
# =============================================================================
# Nuxel VM Bootstrap Script
# Installs and configures Nuxel OS core services inside a UTM ARM64 Linux VM.
#
# Target: aarch64 Linux VM (Fedora ARM64 / Debian ARM64 via UTM on Apple Silicon)
# Prerequisites: UTM VM with working Phosh session, sudo access, internet
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# ── Configuration ──────────────────────────────────────────────────────────

NUXEL_USER="${NUXEL_USER:-nuxel}"
# Repo root: where the Nuxel project sources live on the host. The script is staged
export NUXEL_ROOT="${NUXEL_ROOT:-$(cd "$(cd "$(dirname "$0")" && pwd)/.." && pwd)}"
NUXEL_UID="${NUXEL_UID:-1000}"
NUXEL_HOME="/home/${NUXEL_USER}"
NUXEL_BASE="${NUXEL_BASE:-/opt/nuxel}"
NUXEL_CONFIG_DIR="${NUXEL_CONFIG_DIR:-/etc/nuxel}"
NUXEL_DATA_DIR="${NUXEL_DATA_DIR:-/var/lib/nuxel}"
NUXEL_APP_DIR="${NUXEL_APP_DIR:-/var/app}"
NUXEL_PERMISSIONS_DIR="${NUXEL_DATA_DIR}/permissions"
NUXEL_SANDBOX_DIR="${NUXEL_BASE}/sandbox"

# Init-system selection (briq-21): this VM bootstrap targets the
# Fedora/UVM VM which uses systemd. Default to systemd but honor an explicit
# NUXEL_INIT override so the same script can stage an OpenRC rootfs if ever
# invoked for the mustang target.
export NUXEL_INIT="${NUXEL_INIT:-systemd}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DISTRO_ID=""

# ── Helper Functions ──────────────────────────────────────────────────────

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_ID="${ID}"
        log_info "Detected distribution: ${ID} ${VERSION_ID:-}"
    else
        log_error "Cannot detect distribution (no /etc/os-release)"
        exit 1
    fi
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (sudo)"
        exit 1
    fi
}

check_phosh() {
    if command -v phosh &>/dev/null; then
        log_info "Phosh shell detected"
        return 0
    fi
    log_warn "Phosh shell not detected — install it first or run phosh-phone-resolution.sh"
    return 1
}

# ── Step 0: System Prerequisites ──────────────────────────────────────────

install_prerequisites() {
    log_info "Installing system prerequisites..."

    # NOTE: gdbus (used by verify_installation's org.nuxel.Portal.Ping check)
    # is provided by the base 'glib2' package on Fedora (no glib2-utils
    # package exists there); Debian/Ubuntu ship it in libglib2.0-bin.
    case "${DISTRO_ID}" in
        fedora)
            dnf install -y \
                wayland-devel \
                gtk4-devel \
                libadwaita-devel \
                dbus-devel \
                pipewire-devel \
                flatpak \
                bubblewrap \
                nftables \
                wl-clipboard \
                wlr-randr \
                NetworkManager \
                git \
                python3-dbus \
                python3-gobject \
                python3-pip \
                glib2-devel \
                meson \
                ninja-build \
                gcc \
                gcc-c++ \
                pkg-config \
                lz4 \
                xdg-desktop-portal-gtk \
                xdg-desktop-portal
            ;;
        debian|ubuntu)
            apt-get update
            apt-get install -y \
                libwayland-dev \
                libgtk-4-dev \
                libadwaita-1-dev \
                libdbus-1-dev \
                libpipewire-0.3-dev \
                flatpak \
                bubblewrap \
                apparmor-utils \
                apparmor-profiles \
                nftables \
                wl-clipboard \
                wlr-randr \
                network-manager \
                git \
                python3-dbus \
                python3-gi \
                python3-pip \
                libglib2.0-dev \
                meson \
                ninja-build \
                gcc \
                g++ \
                pkg-config \
                liblz4-dev \
                libglib2.0-bin \
                xdg-desktop-portal-gtk \
                xdg-desktop-portal
            ;;
        *)
            log_warn "Unknown distro ${DISTRO_ID}. Attempting generic install..."
            log_warn "Install prerequisites manually: GTK4, libadwaita, dbus, bubblewrap, apparmor, nftables, flatpak"
            ;;
    esac

    log_info "Prerequisites installed"
}

# ── Step 1: Create nuxel User ────────────────────────────────────────────

create_nuxel_user() {
    log_info "Creating nuxel user..."

    if id "${NUXEL_USER}" &>/dev/null; then
        log_info "User ${NUXEL_USER} already exists"
        return 0
    fi

    # Helper: filter a comma-separated group list down to groups that exist
    # on the target distro. useradd aborts if any listed group is missing
    # (e.g. adb/docker absent on a minimal Fedora), which would trip set -e.
    existing_groups() {
        local out=""
        IFS=',' read -ra _grps <<< "$1"
        for g in "${_grps[@]}"; do
            if getent group "${g}" &>/dev/null; then
                out="${out:+${out},}${g}"
            else
                log_warn "  group '${g}' missing -- skipping membership"
            fi
        done
        echo "${out}"
    }

    case "${DISTRO_ID}" in
        fedora)
            useradd \
                --create-home \
                --uid "${NUXEL_UID}" \
                --groups "$(existing_groups "wheel,adb,input,video,audio,netdev,docker")" \
                --shell /bin/bash \
                --comment "Nuxel OS User" \
                "${NUXEL_USER}" || {
                    log_warn "useradd with groups failed -- retrying without groups"
                    useradd --create-home --uid "${NUXEL_UID}" \
                        --shell /bin/bash --comment "Nuxel OS User" "${NUXEL_USER}"
                }
            ;;
        debian|ubuntu)
            useradd \
                --create-home \
                --uid "${NUXEL_UID}" \
                --groups "$(existing_groups "sudo,input,video,audio,netdev")" \
                --shell /bin/bash \
                --comment "Nuxel OS User" \
                "${NUXEL_USER}" || {
                    log_warn "useradd with groups failed -- retrying without groups"
                    useradd --create-home --uid "${NUXEL_UID}" \
                        --shell /bin/bash --comment "Nuxel OS User" "${NUXEL_USER}"
                }
            ;;
        *)
            useradd --create-home --uid "${NUXEL_UID}" "${NUXEL_USER}"
            ;;
    esac

    # Set empty password (user changes later via passwd)
    passwd -d "${NUXEL_USER}" 2>/dev/null || true

    # Sudo without password for nuxel user (development profile)
    if command -v visudo &>/dev/null; then
        echo "${NUXEL_USER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/nuxel
        chmod 0440 /etc/sudoers.d/nuxel
    else
        log_warn "sudo not installed -- skipped /etc/sudoers.d/nuxel"
    fi

    log_info "User ${NUXEL_USER} created"
}


# ── Dedicated service system users (repo unit files reference these) ─────
# services/*/systemd/*.service run bridge/portal/notifications under dedicated
# users. The D-Bus policies under services/*/dbus/*.conf explicitly allow
# user="nuxel-bridge"/"nuxel-portal"/"nuxel-notifications" to interact, so we
# create them here. Idempotent; a missing system user would otherwise make the
# repo unit files fail to launch ("User ... not found").

create_service_users() {
    log_info "Creating dedicated system service users..."
    local svc_user
    for svc_user in nuxel-bridge nuxel-portal nuxel-notifications; do
        if ! id "${svc_user}" &>/dev/null; then
            useradd --system --no-create-home --shell /usr/sbin/nologin                 --comment "Nuxel system service account" "${svc_user}" 2>/dev/null &&                 log_info "  created user ${svc_user}" ||                 log_warn "  could not create user ${svc_user} (continue)"
        else
            log_info "  user ${svc_user} already exists"
        fi
        # Give the service users group membership in 'nuxel' so the default
        # D-Bus group policy lets them reach the bridge/portal/notifications.
        if getent group nuxel &>/dev/null; then
            usermod -a -G nuxel "${svc_user}" 2>/dev/null || true
        fi
    done
}

# ── Step 2: Create Nuxel Directory Layout ─────────────────────────────────

create_directory_layout() {
    log_info "Creating Nuxel directory layout..."

    mkdir -p "${NUXEL_BASE}"
    mkdir -p "${NUXEL_CONFIG_DIR}"
    mkdir -p "${NUXEL_DATA_DIR}"
    mkdir -p "${NUXEL_PERMISSIONS_DIR}"
    mkdir -p "${NUXEL_APP_DIR}"
    mkdir -p "${NUXEL_SANDBOX_DIR}"
    mkdir -p "${NUXEL_HOME}/.config/nuxel"
    mkdir -p "${NUXEL_HOME}/.local/share/applications"
    mkdir -p /etc/apparmor.d

    # Install the single-source path config (briq-20) so services read their
    # canonical paths from /etc/nuxel/paths.conf (overridable via
    # NUXEL_PATHS_CONF).
    if [ -f "${NUXEL_ROOT}/configs/nuxel/paths.conf" ]; then
        install -Dm0644 "${NUXEL_ROOT}/configs/nuxel/paths.conf" /etc/nuxel/paths.conf
        log_info "  /etc/nuxel/paths.conf installed"
    else
        log_warn "  configs/nuxel/paths.conf not found — path config not installed"
    fi

    chown -R "${NUXEL_USER}:${NUXEL_USER}" "${NUXEL_HOME}"
    chmod 755 "${NUXEL_BASE}"
    # Group-writable so the dedicated service users (nuxel-bridge,
    # nuxel-portal, nuxel-notifications — members of group 'nuxel') can
    # persist tokens / notification history / grants under /var/lib/nuxel.
    chmod 770 "${NUXEL_DATA_DIR}"
    chmod 770 "${NUXEL_PERMISSIONS_DIR}"
    # The portal (User=nuxel, see nuxel-portal.service) persists consent
    # grants under ${NUXEL_PERMISSIONS_DIR}; mkdir leaves it root-owned, so
    # hand it to the nuxel user (group 'nuxel' members keep group write).
    chown "${NUXEL_USER}:${NUXEL_USER}" "${NUXEL_PERMISSIONS_DIR}" 2>/dev/null || true
    chmod 770 "${NUXEL_PERMISSIONS_DIR}"
    chmod 755 "${NUXEL_APP_DIR}"

    log_info "Directory layout created"
}

# ── Step 3: Install Nuxel Core Services ───────────────────────────────────

install_nuxel_bridge() {
    log_info "Installing nuxel-bridge service..."

    # Prefer the repo's real bridge (org.nuxel.Bridge with Ping/GetCapabilities/
    # RequestCapability, used by /api/v1/ping round-trip); fall back to the
    # self-contained embedded daemon when the repo payload is absent.
    local BRIDGE_SRC="${NUXEL_ROOT}/services/nuxel-bridge/src/bridge.py"
    if [ -f "${BRIDGE_SRC}" ]; then
        install -D -m0755 "${BRIDGE_SRC}" /usr/local/libexec/nuxel-bridge.py
        log_info "nuxel-bridge payload installed from repo source: ${BRIDGE_SRC}"
    else
        log_warn "Bridge source not found at ${BRIDGE_SRC} -- installing embedded fallback."
        # Create bridge service script
        cat > /usr/local/libexec/nuxel-bridge.py << 'PYEOF'
#!/usr/bin/env python3
"""
Nuxel Bridge — D-Bus permission broker.
Mediates permission checks between portal daemon and apps.
"""
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import json
import os
import logging

BUS_NAME = 'org.nuxel.Bridge'
OBJECT_PATH = '/org/nuxel/Bridge'
PERMISSIONS_DIR = '/var/lib/nuxel/permissions'

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('nuxel-bridge')

class NuxelBridge(dbus.service.Object):
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)
        os.makedirs(PERMISSIONS_DIR, exist_ok=True)
        logger.info("Nuxel Bridge ready")

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def CheckCapability(self, app_id, capability):
        path = os.path.join(PERMISSIONS_DIR, f"{app_id.replace('/', '_')}.json")
        if not os.path.exists(path):
            return json.dumps({'granted': False})
        try:
            with open(path) as f:
                grants = json.load(f)
            cap_data = grants.get(capability, {})
            if cap_data.get('duration') == 'always':
                return json.dumps({'granted': True, 'duration': 'always'})
            return json.dumps({'granted': False})
        except (json.JSONDecodeError, OSError):
            return json.dumps({'granted': False})

    @dbus.service.method(BUS_NAME, in_signature='s', out_signature='s')
    def GetAppPermissions(self, app_id):
        path = os.path.join(PERMISSIONS_DIR, f"{app_id.replace('/', '_')}.json")
        if not os.path.exists(path):
            return json.dumps({'app_id': app_id, 'permissions': {}})
        try:
            with open(path) as f:
                return json.dumps({'app_id': app_id, 'permissions': json.load(f)})
        except (json.JSONDecodeError, OSError):
            return json.dumps({'app_id': app_id, 'permissions': {}})

    @dbus.service.method(BUS_NAME, in_signature='ss', out_signature='s')
    def RevokePermission(self, app_id, capability):
        path = os.path.join(PERMISSIONS_DIR, f"{app_id.replace('/', '_')}.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    grants = json.load(f)
                if capability in grants:
                    del grants[capability]
                with open(path, 'w') as f:
                    json.dump(grants, f, indent=2)
                return json.dumps({'success': True})
            except (json.JSONDecodeError, OSError):
                pass
        return json.dumps({'success': False})

    @dbus.service.signal(BUS_NAME, signature='s')
    def PermissionChanged(self, data):
        pass

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
name = dbus.service.BusName(BUS_NAME, bus)
svc = NuxelBridge(bus, OBJECT_PATH)
GLib.MainLoop().run()
PYEOF
        chmod 755 /usr/local/libexec/nuxel-bridge.py
    fi

    # Create systemd service
    cat > /etc/systemd/system/nuxel-bridge.service << 'SYSEOF'
[Unit]
Description=Nuxel Bridge D-Bus Permission Broker
Documentation=https://github.com/nuxel/docs
After=dbus.service
Requires=dbus.service

[Service]
Type=dbus
BusName=org.nuxel.Bridge
ExecStart=/usr/local/libexec/nuxel-bridge.py
Restart=on-failure
RestartSec=3
User=root
Group=root
CapabilityBoundingSet=CAP_DAC_OVERRIDE CAP_CHOWN CAP_FOWNER CAP_SETUID
NoNewPrivileges=yes
ProtectSystem=full
ProtectHome=yes

[Install]
WantedBy=multi-user.target
SYSEOF

    systemctl daemon-reload 2>/dev/null || true
    systemctl enable nuxel-bridge.service 2>/dev/null || log_warn "could not enable nuxel-bridge.service (continue)"
    log_info "nuxel-bridge installed and enabled"
}

install_nuxel_portal() {
    log_info "Installing nuxel-portal service..."

    # Create portal daemon script (links to project source if available,
    # otherwise deploys a self-contained version)
    local PORTAL_SRC="${NUXEL_ROOT}/services/nuxel-portal/src/portal.py"
    if [ -f "${PORTAL_SRC}" ]; then
        cp "${PORTAL_SRC}" /usr/local/libexec/nuxel-portal.py
    else
        log_warn "Portal source not found at ${PORTAL_SRC}"
        log_warn "Installing a self-contained fallback portal daemon instead."
        # Self-contained fallback so the bootstrap never aborts under set -e
        # when the repo payload is absent on the target VM.
        cat > /usr/local/libexec/nuxel-portal.py << 'PORTALPY'
#!/usr/bin/env python3
"""Nuxel Portal daemon - fallback embed for VM bootstrap (briq-v1)."""
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import json
import logging
import os

BUS_NAME = "org.nuxel.Portal"
OBJ = "/org/nuxel/Portal"
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nuxel-portal")

class NuxelPortal(dbus.service.Object):
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)
        logger.info("Nuxel Portal ready")

    @dbus.service.method(BUS_NAME, in_signature="s", out_signature="s")
    def Ping(self, msg):
        return json.dumps({"pong": msg, "portal": "fallback"})

    @dbus.service.method(BUS_NAME, in_signature="ss", out_signature="s")
    def CheckPermission(self, app_id, capability):
        return json.dumps({"app_id": app_id, "capability": capability, "granted": True})

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
name = dbus.service.BusName(BUS_NAME, bus)
svc = NuxelPortal(bus, OBJ)
GLib.MainLoop().run()
PORTALPY
        chmod 755 /usr/local/libexec/nuxel-portal.py
        log_warn "Installed self-contained nuxel-portal.py fallback"
    fi
    chmod 755 /usr/local/libexec/nuxel-portal.py

    # Create systemd service
    cat > /etc/systemd/system/nuxel-portal.service << 'SYSEOF'
[Unit]
Description=Nuxel Portal Daemon
Documentation=https://github.com/nuxel/docs
After=nuxel-bridge.service dbus.service
Requires=nuxel-bridge.service dbus.service

[Service]
Type=dbus
BusName=org.nuxel.Portal
ExecStart=/usr/local/libexec/nuxel-portal.py
Restart=on-failure
RestartSec=3
# MUST run as the graphical 'nuxel' user (uid 1000): dbus-broker's user-scope
# session bus only accepts connections from the owning uid, so a root (or
# dedicated-service-user) portal can never reach org.nuxel.PhoshAgent on the
# session bus (verified 2026-08-19, bg-09: root -> 'Transport endpoint is not
# connected'). The PhoshAgent renders the consent dialog in the Phosh session;
# the portal only needs the same-uid session-bus connection to forward
# RequestPermission calls and receive the consent JSON back.
User=nuxel
Group=nuxel
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
NoNewPrivileges=yes
ProtectSystem=full
ProtectHome=yes

[Install]
WantedBy=multi-user.target
SYSEOF

    systemctl daemon-reload 2>/dev/null || true
    systemctl enable nuxel-portal.service 2>/dev/null || log_warn "could not enable nuxel-portal.service (continue)"
    log_info "nuxel-portal installed and enabled"
}

install_nuxel_notifications() {
    log_info "Installing nuxel-notifications service..."

    # Prefer the repo's real notification hub (org.nuxel.Notifications with
    # Notify(app_id,summary,body) + NotificationAdded/NotificationClosed
    # signals, which vm-verify-services.sh / vm-verify-phosh-agent.sh assert);
    # fall back to the self-contained embedded daemon when the repo payload is
    # absent.
    local NOTIF_SRC="${NUXEL_ROOT}/services/nuxel-notifications/src/notifications.py"
    if [ -f "${NOTIF_SRC}" ]; then
        install -D -m0755 "${NOTIF_SRC}" /usr/local/libexec/nuxel-notifications.py
        log_info "nuxel-notifications payload installed from repo source: ${NOTIF_SRC}"
    else
        log_warn "Notifications source not found at ${NOTIF_SRC} -- installing embedded fallback."
        # Notification hub script
        cat > /usr/local/libexec/nuxel-notifications.py << 'PYEOF'
#!/usr/bin/env python3
"""
Nuxel Notifications — On-device notification hub with D-Bus API.
"""
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
import json
import logging
import os
import time

BUS_NAME = 'org.nuxel.Notifications'
OBJECT_PATH = '/org/nuxel/Notifications'

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('nuxel-notifications')

NOTIF_DIR = '/var/lib/nuxel/notifications'

class NuxelNotifications(dbus.service.Object):
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)
        os.makedirs(NOTIF_DIR, exist_ok=True)
        self.notifications = {}
        self.counter = 0
        logger.info("Nuxel Notifications ready")

    @dbus.service.method(BUS_NAME, in_signature='sssa{sv}', out_signature='u')
    def Notify(self, app_id, replaces_id, summary, body, hints):
        self.counter += 1
        nid = self.counter
        self.notifications[nid] = {
            'id': nid,
            'app_id': app_id,
            'summary': summary,
            'body': body,
            'timestamp': time.time(),
        }
        self.NotificationReceived(json.dumps(self.notifications[nid]))
        self._persist()
        logger.info(f"Notification {nid}: {app_id} - {summary}")
        return nid

    @dbus.service.method(BUS_NAME, in_signature='u', out_signature='')
    def CloseNotification(self, nid):
        self.notifications.pop(nid, None)
        self._persist()

    @dbus.service.method(BUS_NAME, in_signature='', out_signature='s')
    def GetNotifications(self):
        return json.dumps(list(self.notifications.values()))

    @dbus.service.signal(BUS_NAME, signature='s')
    def NotificationReceived(self, data):
        pass

    def _persist(self):
        try:
            path = os.path.join(NOTIF_DIR, 'notifications.json')
            with open(path, 'w') as f:
                json.dump(list(self.notifications.values()), f)
        except OSError as e:
            logger.error(f"Failed to persist notifications: {e}")

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
name = dbus.service.BusName(BUS_NAME, bus)
svc = NuxelNotifications(bus, OBJECT_PATH)
GLib.MainLoop().run()
PYEOF
        chmod 755 /usr/local/libexec/nuxel-notifications.py
    fi

    cat > /etc/systemd/system/nuxel-notifications.service << 'SYSEOF'
[Unit]
Description=Nuxel Notification Hub
After=dbus.service
Requires=dbus.service

[Service]
Type=dbus
BusName=org.nuxel.Notifications
ExecStart=/usr/local/libexec/nuxel-notifications.py
Restart=on-failure
RestartSec=3
User=root
NoNewPrivileges=yes
# Canonical on-disk history file (single source, verified by
# vm/vm-verify-services.sh at /var/lib/nuxel/notifications.json).
Environment=NUXEL_NOTIFICATIONS_FILE=/var/lib/nuxel/notifications.json
Environment=NUXEL_NOTIFICATIONS_HISTORY_CAP=200

[Install]
WantedBy=multi-user.target
SYSEOF

    systemctl daemon-reload 2>/dev/null || true
    systemctl enable nuxel-notifications.service 2>/dev/null || log_warn "could not enable nuxel-notifications.service (continue)"
    log_info "nuxel-notifications installed and enabled"
}

# ── HTTP Bridge (nuxel-http-bridge.service) ──────────────────────────────

install_nuxel_http_bridge() {
    log_info "Installing nuxel-http-bridge service..."

    # Deploy the HTTP API layer from the repo into the VM libexec path.
    if [ -f "${NUXEL_ROOT}/services/nuxel-bridge/src/api.py" ]; then
        install -D -m0644 "${NUXEL_ROOT}/services/nuxel-bridge/src/api.py" /usr/lib/nuxel/bridge/api.py
        # capabilities.py and bridge helpers must sit next to api.py.
        install -D -m0644 "${NUXEL_ROOT}/services/nuxel-bridge/src/capabilities.py" /usr/lib/nuxel/bridge/capabilities.py
        if [ -f "${NUXEL_ROOT}/services/nuxel-bridge/src/bridge.py" ]; then
            install -D -m0644 "${NUXEL_ROOT}/services/nuxel-bridge/src/bridge.py" /usr/lib/nuxel/bridge/bridge.py
        fi
    else
        log_warn "HTTP bridge api.py not found at ${NUXEL_ROOT}/services/nuxel-bridge/src/api.py"
        log_warn "nuxel-http-bridge service file is still installed, but the payload is missing."
    fi

    # Install the systemd unit (from the repo's canonical unit file).
    if [ -f "${NUXEL_ROOT}/services/nuxel-bridge/systemd/nuxel-http-bridge.service" ]; then
        install -D -m0644             "${NUXEL_ROOT}/services/nuxel-bridge/systemd/nuxel-http-bridge.service"             /etc/systemd/system/nuxel-http-bridge.service
    else
        # Fallback: embed a minimal unit matching the repo's nuxel-http-bridge.service.
        cat > /etc/systemd/system/nuxel-http-bridge.service << 'SYSEOF'
[Unit]
Description=Nuxel HTTP Bridge API
After=dbus.service nuxel-bridge.service
Wants=dbus.service nuxel-bridge.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/lib/nuxel/bridge/api.py
Restart=on-failure
RestartSec=3
User=root
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=yes
RestrictAddressFamilies=AF_INET AF_UNIX
ReadWritePaths=/var/lib/nuxel /var/log/nuxel
Environment=NUXEL_HTTP_BIND=127.0.0.1
Environment=NUXEL_HTTP_PORT=8080
Environment=NUXEL_HTTP_MODE=dev

[Install]
WantedBy=multi-user.target
SYSEOF
    fi

    systemctl daemon-reload 2>/dev/null || true
    systemctl enable nuxel-http-bridge.service 2>/dev/null || log_warn "could not enable nuxel-http-bridge.service (continue)"
    log_info "nuxel-http-bridge installed and enabled (port 8080)"
}

# ── D-Bus Policy (services/*/dbus/*.conf → /etc/dbus-1/system.d/) ───────

install_dbus_policy() {
    log_info "Installing Nuxel D-Bus policy files..."

    mkdir -p /etc/dbus-1/system.d
    local installed=0

    # Copy every service policy file from the repo into the system D-Bus dir.
    for conf in "${NUXEL_ROOT}"/services/*/dbus/*.conf; do
        [ -f "${conf}" ] || continue
        install -m0644 "${conf}" "/etc/dbus-1/system.d/$(basename "${conf}")"
        log_info "  D-Bus policy: $(basename "${conf}")"
        installed=$((installed + 1))
    done

    # Ensure the mandatory policies are present even if the glob matched nothing.
    for pol in org.nuxel.Bridge.conf org.nuxel.Portal.conf org.nuxel.Notifications.conf; do
        if [ ! -f "/etc/dbus-1/system.d/${pol}" ]; then
            log_warn "D-Bus policy ${pol} missing from repo — defaulting to a permissive system policy."
            cat > "/etc/dbus-1/system.d/${pol}" << 'POLSEOF'
<busconfig>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true" own="*"/>
    <allow receive_sender="*" eavesdrop="true"/>
  </policy>
  <policy user="root">
    <allow own="*"/>
  </policy>
</busconfig>
POLSEOF
            installed=$((installed + 1))
        fi
    done

    # Reload the D-Bus config so the new policies take effect.
    if command -v systemctl &>/dev/null; then
        systemctl daemon-reload 2>/dev/null || true
        systemctl reload dbus.service 2>/dev/null || systemctl restart dbus.service 2>/dev/null || true
    fi
    log_info "Installed ${installed} D-Bus policy file(s) and reloaded system D-Bus config."
}


# ── Python venv at /opt/nuxel (briq-4 Step 3) ────────────────────────────
# Creates a project venv rooted at ${NUXEL_BASE} (/opt/nuxel) with
# --system-site-packages so the dnf-installed python3-dbus / python3-gobject
# remain importable. Any project pip deps declared under services/*/requirements*.txt
# or pwa/*/requirements*.txt are installed into the venv.

create_python_venv() {
    log_info "Creating Python venv at ${NUXEL_BASE}/.venv ..."
    mkdir -p "${NUXEL_BASE}"
    local PY=""

    if command -v python3 >/dev/null 2>&1; then
        PY="python3"
    elif command -v python3.12 >/dev/null 2>&1; then
        PY="python3.12"
    elif command -v python3.11 >/dev/null 2>&1; then
        PY="python3.11"
    else
        log_warn "No python3 found — skipping venv creation."
        return 0
    fi

    if [ ! -x "${NUXEL_BASE}/.venv/bin/${PY}" ]; then
        if "${PY}" -m venv --system-site-packages "${NUXEL_BASE}/.venv"; then
            log_info "  venv created at ${NUXEL_BASE}/.venv (system-site-packages)"
        else
            log_warn "  python -m venv failed; continuing with system python3 (embedded services still run)."
        fi
    else
        log_info "  venv already present at ${NUXEL_BASE}/.venv (idempotent re-run)"
    fi

    # Record the venv executable in paths.conf commentary for the report &
    # install any project requirements*.txt that exist in the repo.
    local req
    for req in "${NUXEL_ROOT}"/services/*/requirements*.txt "${NUXEL_ROOT}"/pwa/*/requirements*.txt; do
        [ -f "${req}" ] || continue
        if [ -x "${NUXEL_BASE}/.venv/bin/pip" ]; then
            log_info "  pip install $(basename "${req}")"
            "${NUXEL_BASE}/.venv/bin/pip" install -q -r "${req}" 2>/dev/null ||                 log_warn "  failed to pip-install from ${req}"
        fi
    done

    chmod -R a+rX "${NUXEL_BASE}/.venv" 2>/dev/null || true
    log_info "Python venv configured at ${NUXEL_BASE}/.venv"
}

# ── Step 4: Hardened Configs ─────────────────────────────────────────────

install_apparmor_profiles() {
    log_info "Installing AppArmor profiles..."

    # Nuxel base profile
    cat > /etc/apparmor.d/nuxel-base << 'PROFEOF'
# Nuxel Base AppArmor Profile
# Applied to all Nuxel-sandboxed applications
abi <abi/4.0>,
include <tunables/global>

profile nuxel-base flags=(attach_disconnected,mediate_deleted) {
    #include <abstractions/base>
    #include <abstractions/dbus>
    #include <abstractions/nameservice>

    # Nuxel system paths
    /opt/nuxel/** r,
    /etc/nuxel/** r,
    /var/lib/nuxel/** rw,

    # App data directories
    /var/app/** rw,

    # Permission files
    /var/lib/nuxel/permissions/** rw,

    # Wayland socket
    /run/user/*/wayland-* rw,
    /run/user/*/phosh_wayland-* rw,

    # PipeWire
    /run/user/*/pipewire-* rw,

    # Portal D-Bus
    dbus bus=system,
    dbus bus=session,

    # PulseAudio / PipeWire audio
    /run/user/*/pulse/** rw,
    /run/user/*/wireplumber-* rw,

    # Deny raw device access
    /dev/tty* r,
    /dev/input/** rw,
    deny /dev/mem rw,
    deny /dev/kmem rw,
    deny /dev/port rw,

    # Deny /etc/shadow
    deny /etc/shadow r,
    deny /etc/gshadow r,

    # Deny other users' home
    deny /home/*/.ssh/** rw,
    deny /home/*/.gnupg/** rw,
}
PROFEOF

    # Nuxel privileged profile (for system services)
    cat > /etc/apparmor.d/nuxel-privileged << 'PROFEOF'
abi <abi/4.0>,
include <tunables/global>

profile nuxel-privileged flags=(attach_disconnected,mediate_deleted) {
    #include <abstractions/base>
    #include <abstractions/dbus>

    /opt/nuxel/** rw,
    /etc/nuxel/** rw,
    /var/lib/nuxel/** rw,
    /var/app/** rw,
    /run/user/*/wayland-* rw,
    /run/user/*/pipewire-* rw,

    # Full system access for privileged tools
    /sys/** r,
    /proc/** rw,
    /dev/** rw,
    /etc/** rw,
    /bin/** ix,
    /usr/bin/** ix,
}
PROFEOF


    # Load profiles
    if command -v aa-enforce &>/dev/null; then
        aa-enforce /etc/apparmor.d/nuxel-base 2>/dev/null || true
        aa-enforce /etc/apparmor.d/nuxel-privileged 2>/dev/null || true
        log_info "AppArmor profiles loaded"
    else
        log_warn "aa-enforce not found — profiles installed but not enforced"
    fi
}

install_hardened_malloc() {
    log_info "Installing hardened memory allocator..."

    # hardened_malloc is applied PER-SERVICE, never globally via
    # /etc/ld.so.preload. A global preload injects the strict allocator into
    # every process (GTK, Phosh, glycin/bwrap SVG loaders, ...), and
    # hardened_malloc aborts on the first malloc() that runs through
    # libstdc++'s static initializers. On this Fedora/UTM image that crashes
    # phosh and stevia immediately, leaving a black, resolution-oscillating
    # display. So: build the library, then scope it to the Nuxel systemd
    # services only (see configs/hardened-malloc.service.d/00-nuxel.conf).

    # 1) Unbreak any VM that a previous bootstrap poisoned with a global preload.
    if [ -f /etc/ld.so.preload ] && grep -q "libhardened_malloc.so" /etc/ld.so.preload 2>/dev/null; then
        log_warn "removing global libhardened_malloc.so from /etc/ld.so.preload (breaks Phosh/GTK)"
        sed -i '\|libhardened_malloc.so|d' /etc/ld.so.preload
        ldconfig || true
    fi

    # 2) Build/install the library if absent (idempotent).
    if [ ! -f /usr/local/lib/libhardened_malloc.so ]; then
        if command -v git &>/dev/null; then
            local TMPDIR
            TMPDIR=$(mktemp -d)
            cd "${TMPDIR}"

            if git clone --depth=1 https://github.com/GrapheneOS/hardened_malloc.git 2>/dev/null; then
                cd hardened_malloc
                if make -j"$(nproc)" 2>/dev/null; then
                    cp out/libhardened_malloc.so /usr/local/lib/
                    ldconfig
                    log_info "hardened_malloc built and installed to /usr/local/lib"
                else
                    log_warn "hardened_malloc build failed — will use system allocator"
                fi
            else
                log_warn "Could not clone hardened_malloc — will use system allocator"
            fi

            cd /
            rm -rf "${TMPDIR}"
        else
            log_warn "git not available — skipping hardened_malloc build"
        fi
    else
        log_info "  /usr/local/lib/libhardened_malloc.so already present — skipping rebuild"
    fi

    # 3) Scope the allocator to Nuxel system services via a systemd drop-in
    #    (NOT globally). Graphical/GTK apps (phosh, stevia, kiosk, portal UI)
    #    deliberately stay on the system allocator.
    if [ -f /usr/local/lib/libhardened_malloc.so ] \
       && [ -f "${NUXEL_ROOT}/configs/hardened-malloc.service.d/00-nuxel.conf" ]; then
        for svc in nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications nuxel-web nuxel-apparmor-enforce; do
            if [ -f "/etc/systemd/system/${svc}.service" ]; then
                mkdir -p "/etc/systemd/system/${svc}.service.d"
                cp "${NUXEL_ROOT}/configs/hardened-malloc.service.d/00-nuxel.conf" \
                   "/etc/systemd/system/${svc}.service.d/00-nuxel.conf"
            fi
        done
        log_info "hardened_malloc scoped to Nuxel system services (per-service drop-in)"
    fi
}

install_nftables_rules() {
    log_info "Installing nftables base ruleset..."

    cat > /etc/nftables.conf << 'NFTEOF'
#!/usr/sbin/nft -f

flush ruleset

table inet nuxel-base {
    # Default: allow established connections, drop inbound
    chain input {
        type filter hook input priority 0; policy drop;

        # Allow loopback
        iif "lo" accept

        # Allow established/related
        ct state established,related accept

        # Allow SSH (development only)
        tcp dport 22 accept

        # Allow mDNS
        udp dport 5353 accept

        # Allow DHCP
        udp dport 67 accept
        udp dport 68 accept

        # Allow ICMP
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept

        # Log then drop
        log prefix "NUXEL-DROP: " flags all
        counter drop
    }

    chain forward {
        type filter hook forward priority 0; policy drop;
    }

    chain output {
        type filter hook output priority 0; policy accept;
    }
}

# Per-app network rules table (populated dynamically)
table inet nuxel-apps {
    chain app-input {
        type filter hook input priority 5; policy accept;
    }

    chain app-output {
        type filter hook output priority 5; policy accept;
    }

    chain app-forward {
        type filter hook forward priority 5; policy drop;
    }
}
NFTEOF

    systemctl enable nftables 2>/dev/null || true
    systemctl restart nftables 2>/dev/null || true
    log_info "nftables base ruleset installed"
}

# Install the hardened Nuxel sandbox launcher wrapper, AppArmor enforce-mode
# unit, and NetworkManager privacy defaults. (briq-15)
install_security_hardening() {
    log_info "Installing nuxel-sandbox launcher + AppArmor enforce + NetworkManager defaults..."

    # ── 1. nuxel-sandbox launcher wrapper ─────────────────────────────────
    # The VM bootstrap builds shell/nuxel-shell/nuxel-sandbox/sandbox.c into
    # /usr/local/bin/nuxel-sandbox. Every PWA / native app launch goes through
    # this wrapper which explicitly enables seccomp BPF + Landlock (both also
    # ON by default in sandbox.c) and names the per-app cgroup that the
    # configs/nftables/nuxel-app-firewall.nft ruleset matches via
    # "socket cgroupv2 level 2 'app-*'". See docs/security-defaults.md.
    # sandbox.c may live either in the staged NUXEL_SANDBOX_DIR or in the repo.
    local sandbox_src=""
    if [ -f "${NUXEL_SANDBOX_DIR}/sandbox.c" ]; then
        sandbox_src="${NUXEL_SANDBOX_DIR}"
    elif [ -f "${NUXEL_ROOT}/shell/nuxel-shell/nuxel-sandbox/sandbox.c" ]; then
        sandbox_src="${NUXEL_ROOT}/shell/nuxel-shell/nuxel-sandbox"
    fi
    if [ -n "${sandbox_src}" ]; then
        if ( cd "${sandbox_src}" && gcc -O2 -Wall -o /usr/local/bin/nuxel-sandbox sandbox.c -lcap -I. 2>/dev/null ); then
            :
        else
            ( cd "${sandbox_src}" && gcc -O2 -Wall -o /usr/local/bin/nuxel-sandbox sandbox.c -I. )
        fi
        chmod 0755 /usr/local/bin/nuxel-sandbox
        log_info "nuxel-sandbox built from ${sandbox_src}/sandbox.c"
    else
        log_warn "sandbox.c not found (checked ${NUXEL_SANDBOX_DIR} and repo) — skipping build"
    fi

    # Wrapper that always enables seccomp + Landlock for a launched PWA/app
    # and forwards the per-app cgroup id. Installed as nuxel-sandbox-run
    # so launcher .desktop files can use: exec /usr/local/bin/nuxel-sandbox-run <app-id> <cmd>
    cat > /usr/local/bin/nuxel-sandbox-run << 'SANDBOX_RUN'
#!/usr/bin/env bash
# Nuxel hardened sandbox launcher wrapper (briq-15).
# Usage: nuxel-sandbox-run <app-id> -- <command> [args...]
# Always enables seccomp BPF + Landlock and names the per-app cgroup so the
# nftables per-app rules apply. Network is granted only when the app holds
# the network capability (stored in /var/lib/nuxel/permissions/<app-id>.json,
# capability "network" with duration == "always"); denied apps stay
# deny-by-default and fall through to the nftables cgroup DROP rule.
set -euo pipefail
app_id="${1:-}"; shift || true
NET_FLAG=""
perm_file="/var/lib/nuxel/permissions/${app_id}.json"
if [ -f "$perm_file" ]; then
    # Parse the stored grant: network capability granted only when
    # reported with duration "always" (matches nuxel-bridge CheckCapability).
    if python3 -c '
import json,sys
try:
    grants=json.load(open(sys.argv[1]))
    d=grants.get("network",{})
    sys.exit(0 if d.get("duration")=="always" else 1)
except Exception:
    sys.exit(1)
' "$perm_file" 2>/dev/null; then
        NET_FLAG="--network"
    fi
elif [ -f "/var/lib/nuxel/permissions/${app_id}.network" ]; then
    # Legacy per-app marker: presence grants network access.
    NET_FLAG="--network"
fi
exec /usr/local/bin/nuxel-sandbox --cgroup "${app_id}" --seccomp --landlock ${NET_FLAG} "$@"
SANDBOX_RUN
    chmod 0755 /usr/local/bin/nuxel-sandbox-run

    # ── 2. AppArmor enforce-mode service (systemd/OpenRC) ─────────────────
    if [ -d /etc/systemd/system ]; then
        install -D -m0644 \
            "${NUXEL_ROOT}/configs/apparmor/systemd/nuxel-apparmor-enforce.service" \
            /etc/systemd/system/nuxel-apparmor-enforce.service
        systemctl daemon-reload 2>/dev/null || true
        systemctl enable nuxel-apparmor-enforce.service 2>/dev/null || true
        # Repair cycle bg-05 (2026-08-19): clear any failed state left by a
        # pre-fix unit (invalid Documentation= URL) and (re)start the oneshot
        # so a bootstrap re-run never leaves it listed in `systemctl --failed`.
        # The unit degrades gracefully (exit 0 + logged SKIP) when the VM
        # kernel/userspace lacks AppArmor.
        systemctl reset-failed nuxel-apparmor-enforce.service 2>/dev/null || true
        systemctl start nuxel-apparmor-enforce.service 2>/dev/null || true
        log_info "nuxel-apparmor-enforce.service installed, enabled and (re)started"
    else
        # OpenRC (postmarketOS/Alpine) fallback
        install -D -m0755 \
            "${NUXEL_ROOT}/configs/apparmor/openrc/nuxel-apparmor" \
            /etc/init.d/nuxel-apparmor
        rc-update add nuxel-apparmor default 2>/dev/null || true
        log_info "OpenRC nuxel-apparmor init script installed and added"
    fi

    # Copy the nuxel AppArmor profiles into place and validate them.
    if [ -d /etc/apparmor.d ]; then
        for prof in "${NUXEL_ROOT}/configs/apparmor.d/"*; do
            [ -f "$prof" ] || continue
            install -m0644 "$prof" "/etc/apparmor.d/$(basename "$prof")"
            if command -v apparmor_parser >/dev/null 2>&1; then
                if apparmor_parser -Q -O enforce "/etc/apparmor.d/$(basename "$prof")" >/dev/null 2>&1; then
                    echo "  validated: $(basename "$prof")"
                else
                    log_warn "invalid profile skipped: $(basename "$prof")"
                fi
            fi
        done
        log_info "AppArmor profiles copied (nuxel-*)"
    fi

    # ── 3. NetworkManager privacy defaults (MAC randomization + DoH) ─────
    if [ -d /etc/NetworkManager/conf.d ]; then
        install -D -m0644 \
            "${NUXEL_ROOT}/configs/networkmanager/98-nuxel-defaults.conf" \
            /etc/NetworkManager/conf.d/98-nuxel-defaults.conf
        install -D -m0644 \
            "${NUXEL_ROOT}/configs/networkmanager/98-nuxel-dns.conf" \
            /etc/NetworkManager/conf.d/98-nuxel-dns.conf
        systemctl restart NetworkManager 2>/dev/null || true
        log_info "NetworkManager privacy defaults applied"
    else
        log_warn "NetworkManager conf dir not found; skipped"
    fi

    # ── 4. Per-app nftables firewall (cgroupv2 socket matching) ──────────
    # The canonical ruleset (with "socket cgroupv2 level 2 'app-*'" matches)
    # is installed; nuxel-sandbox's nftables.sh injects per-app ACCEPT rules.
    if command -v nft >/dev/null 2>&1 && [ -f "${NUXEL_ROOT}/configs/nftables/nuxel-app-firewall.nft" ]; then
        install -D -m0644 \
            "${NUXEL_ROOT}/configs/nftables/nuxel-app-firewall.nft" \
            /etc/nuxel/nftables/nuxel-app-firewall.nft
        nft -f /etc/nuxel/nftables/nuxel-app-firewall.nft 2>/dev/null || true
        log_info "Per-app nftables firewall ruleset installed"
    fi

    log_info "security hardening installed"
}


# ── Flatpak runtime (briq-4; network-fallback) ───────────────────────────
# Installs the org.gnome.Platform//46 runtime for sandboxed PWA apps. If the
# flatpak/flatpakremote add or install fails (no network / repo unavailable),
# we DO NOT abort: the VM proceeds with the standard Fedora/Phosh install and
# logs the fallback so the report can note that sandboxed apps fall back to
# the local launcher instead of the Flatpak runtime.

install_flatpak_runtime() {
    log_info "Installing Flatpak GNOME runtime (org.gnome.Platform//46)..."
    if ! command -v flatpak >/dev/null 2>&1; then
        log_warn "  flatpak not installed — skipping Flatpak runtime (use standard Fedora/Phosh install)."
        return 0
    fi
    # Idempotent: locate the flathub remote; add if missing.
    if ! flatpak remotes 2>/dev/null | grep -qi "flathub"; then
        flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo 2>/dev/null             || { log_warn "  could not add flathub remote (network?) — proceeding with standard install."; return 0; }
    fi
    if flatpak list --runtime 2>/dev/null | grep -q "org.gnome.Platform//46"; then
        log_info "  org.gnome.Platform//46 already installed"
        return 0
    fi
    if flatpak install -y --noninteractive flathub org.gnome.Platform//46 2>/dev/null; then
        log_info "  org.gnome.Platform//46 runtime installed"
    else
        log_warn "  Flatpak org.gnome.Platform//46 install FAILED (network). Falling back to standard Fedora/Phosh install."
        log_warn "  REPORT: sandboxed PWA apps will use the local launcher rather than the Flatpak runtime."
    fi
}
# ── Step 5: Configure Phosh for Mobile UX ────────────────────────────────

configure_phosh() {
    log_info "Configuring Phosh for mobile UX..."

    # Create Phosh config
    # Install Nuxel wallpaper (single source: assets/nuxel-background.png, briq-23)
    mkdir -p /usr/share/nuxel/wallpapers /usr/share/backgrounds/nuxel
    if [ -f "${NUXEL_ROOT}/assets/nuxel-background.png" ]; then
        cp "${NUXEL_ROOT}/assets/nuxel-background.png" /usr/share/nuxel/wallpapers/nuxel-background.png
        cp "${NUXEL_ROOT}/assets/nuxel-background.png" /usr/share/backgrounds/nuxel/default.png
        ln -sf /usr/share/nuxel/wallpapers/nuxel-background.png /usr/share/backgrounds/nuxel/lockscreen.png 2>/dev/null || true
        log_info "Nuxel wallpaper installed"
    fi

    # Install boot animation (single source: assets/nuxel-boot-animation.mp4, briq-23)
    mkdir -p /usr/share/nuxel/boot
    if [ -f "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4" ]; then
        cp "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4" /usr/share/nuxel/boot/nuxel-boot-animation.mp4
        log_info "Boot animation installed"
    fi

    # Populate per-app PWA assets from the single-source assets/ tree
    # (briq-23). No wallpaper duplicates are checked in; the canonical copy
    # is copied into each app's assets/ at build time.
    if [ -x "${NUXEL_ROOT}/tools/dedupe-assets.sh" ]; then
        "${NUXEL_ROOT}/tools/dedupe-assets.sh" || true
        log_info "PWA asset directories populated (via dedupe-assets.sh)"
    else
        log_warn "tools/dedupe-assets.sh missing — skipping PWA asset population"
    fi

    mkdir -p "${NUXEL_HOME}/.config/phosh"
    cat > "${NUXEL_HOME}/.config/phosh/phosh.ini" << 'PHOSHEOF'
[shell]
lockdown-mode=on
show-window-preview=true
show-background=true
show-top-bar=true
max-notifications=5
background=/usr/share/backgrounds/nuxel/default.png

[lock-screen]
show-background=true
idle-timeout-sec=60
background=/usr/share/backgrounds/nuxel/lockscreen.png

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

    chown -R "${NUXEL_USER}:${NUXEL_USER}" "${NUXEL_HOME}/.config/phosh"

    # Set up autologin for nuxel user (greeter config)
    if [ -f /etc/gdm/custom.conf ]; then
        sed -i 's/^#  AutomaticLoginEnable = true/AutomaticLoginEnable = true/' /etc/gdm/custom.conf
        sed -i 's/^#  AutomaticLogin = user1/AutomaticLogin = nuxel/' /etc/gdm/custom.conf
    fi

    if [ -f /etc/lightdm/lightdm.conf ]; then
        cat >> /etc/lightdm/lightdm.conf << 'LIGHTDMEOF'
[Seat:*]
autologin-user=nuxel
autologin-user-timeout=0
user-session=phosh
LIGHTDMEOF
    fi

    # Install Nuxel Home kiosk launcher
    if [ -f "${NUXEL_ROOT}/shell/nuxel-kiosk/nuxel-home-kiosk" ]; then
        mkdir -p /home/${NUXEL_USER}/bin
        install -Dm755 "${NUXEL_ROOT}/shell/nuxel-kiosk/nuxel-home-kiosk"             /home/${NUXEL_USER}/bin/nuxel-home-kiosk
        chown ${NUXEL_USER}:${NUXEL_USER} /home/${NUXEL_USER}/bin/nuxel-home-kiosk
        log_info "nuxel-home-kiosk installed"
    fi

    # Install desktop entry (Phosh app drawer)
    if [ -f "${NUXEL_ROOT}/shell/config/nuxel-home.desktop" ]; then
        mkdir -p /home/${NUXEL_USER}/.local/share/applications
        sed "s|/home/wicked|/home/${NUXEL_USER}|g"             "${NUXEL_ROOT}/shell/config/nuxel-home.desktop"             > /home/${NUXEL_USER}/.local/share/applications/nuxel-home.desktop
        chown ${NUXEL_USER}:${NUXEL_USER} /home/${NUXEL_USER}/.local/share/applications/nuxel-home.desktop
        log_info "nuxel-home.desktop installed"
    fi

    # Install Nuxel Home kiosk as systemd user service
    mkdir -p /home/${NUXEL_USER}/.config/systemd/user
    if [ -f "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-home-kiosk.service" ]; then
        sed "s|/home/wicked|/home/${NUXEL_USER}|g"             "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-home-kiosk.service"             > /home/${NUXEL_USER}/.config/systemd/user/nuxel-home-kiosk.service
        chown -R ${NUXEL_USER}:${NUXEL_USER} /home/${NUXEL_USER}/.config/systemd
        log_info "nuxel-home-kiosk.service installed (user)"
    fi

    # Also install native Home launcher + systemd service (do NOT disable kiosk)
    if [ -f "${NUXEL_ROOT}/shell/nuxel-home-native/nuxel-home-launcher" ]; then
        cp "${NUXEL_ROOT}/shell/nuxel-home-native/nuxel-home-launcher" /usr/local/bin/nuxel-home
        chmod +x /usr/local/bin/nuxel-home
        log_info "nuxel-home native launcher installed"
    fi
    if [ -f "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-home-native.service" ]; then
        sed "s|/home/wicked|/home/${NUXEL_USER}|g"             "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-home-native.service"             > /home/${NUXEL_USER}/.config/systemd/user/nuxel-home-native.service
        chown ${NUXEL_USER}:${NUXEL_USER} /home/${NUXEL_USER}/.config/systemd/user/nuxel-home-native.service
        log_info "nuxel-home-native.service installed (disabled by default)"
    fi
    # Deploy the PhoshAgent executable BEFORE installing its user unit so
    # the ExecStart=/usr/local/bin/nuxel-phosh-agent target actually exists
    # (otherwise the Type=dbus unit would fail to start: 'command not found').
    if [ -f "${NUXEL_ROOT}/shell/nuxel-phosh-agent/nuxel-phosh-agent.py" ]; then
        cp "${NUXEL_ROOT}/shell/nuxel-phosh-agent/nuxel-phosh-agent.py" /usr/local/bin/nuxel-phosh-agent
        chmod +x /usr/local/bin/nuxel-phosh-agent
        log_info "nuxel-phosh-agent executable deployed to /usr/local/bin/nuxel-phosh-agent"
    else
        log_warn "nuxel-phosh-agent.py not found -- skipping PhoshAgent deploy"
    fi
    if [ -f "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-phosh-agent.service" ]; then
        sed "s|/home/wicked|/home/${NUXEL_USER}|g"             "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-phosh-agent.service"             > /home/${NUXEL_USER}/.config/systemd/user/nuxel-phosh-agent.service
        chown ${NUXEL_USER}:${NUXEL_USER} /home/${NUXEL_USER}/.config/systemd/user/nuxel-phosh-agent.service
        log_info "nuxel-phosh-agent.service installed"
        # Enable for the user session so it auto-starts (Type=dbus on the
        # session bus) and can be D-Bus activated via a org.nuxel.PhoshAgent
        # request. Installed into default.target.wants as a fallback; the
        # systemctl --user enable is best-effort during bootstrap.
        mkdir -p /home/${NUXEL_USER}/.config/systemd/user/default.target.wants
        ln -sf /home/${NUXEL_USER}/.config/systemd/user/nuxel-phosh-agent.service \
            /home/${NUXEL_USER}/.config/systemd/user/default.target.wants/nuxel-phosh-agent.service
        chown -R ${NUXEL_USER}:${NUXEL_USER} /home/${NUXEL_USER}/.config/systemd/user
        if command -v systemctl >/dev/null 2>&1; then
            su -s /bin/bash ${NUXEL_USER} -c                 "systemctl --user daemon-reload >/dev/null 2>&1 || true;                  systemctl --user enable nuxel-phosh-agent.service >/dev/null 2>&1 || true"                 >/dev/null 2>&1 || true
        fi
        log_info "nuxel-phosh-agent.service enabled for the user session"
        fi

    # Install a deterministic phoc (compositor) config for the UTM virtio-gpu
    # output. This both (a) makes the 720x1440 portrait mode available via a
    # custom modeline (virtio-gpu EDID does not advertise it) and (b) pins the
    # output rotation to normal with DRM panel-orientation auto-rotation off,
    # so Phosh never renders the framebuffer sideways or upside down.
    cat > /usr/share/phosh/phoc.ini << 'PHOCEOF'
[core]
xwayland = false

[output:Virtual-1]
# UTM/QEMU virtual monitor (virtio-gpu-gl-pci): phone-like portrait geometry.
modeline = 87.25  720 776 848 976  1440 1443 1453 1493 -hsync +vsync
mode = 720x1440
scale = 2
rotate = normal
drm-panel-orientation = false
PHOCEOF
    log_info "phoc.ini installed (720x1440 portrait, rotation locked to normal)"

    # Force wlroots to use legacy (non-atomic) DRM modesetting for the UTM
    # virtio-gpu output, and render the cursor in software.
    #
    # Root cause of the upside-down/dislocated cursor and the sideways
    # landscape rotation: virtio-gpu (QEMU/virglrenderer) has broken atomic
    # modesetting — every atomic commit returns EBUSY
    # ("Atomic commit failed: Device or resource busy"), which makes phoc
    # retry constantly and leaves the cursor plane/output transform in an
    # inconsistent state. WLR_DRM_NO_ATOMIC=1 switches wlroots to the legacy
    # DRM modesetting ioctls (which virtio-gpu supports correctly), fixing
    # both the cursor and the rotation. WLR_NO_HARDWARE_CURSORS=1 is a
    # belt-and-suspenders software-cursor override for the broken virtio-gpu
    # hardware cursor plane.
    #
    # phosh-session sources $HOME/.phoshdebug before exec'ing phoc, so this
    # file is the supported way to set compositor env vars for Phosh.
    cat > "/home/${NUXEL_USER}/.phoshdebug" << 'PHOSHDEBUGEOF'
# Nuxel: force legacy (non-atomic) DRM modesetting + software cursors on the
# UTM virtio-gpu display. Fixes the upside-down/dislocated cursor and the
# sideways landscape rotation.
export WLR_DRM_NO_ATOMIC=1
export WLR_NO_HARDWARE_CURSORS=1
PHOSHDEBUGEOF
    chown "${NUXEL_USER}:${NUXEL_USER}" "/home/${NUXEL_USER}/.phoshdebug"
    log_info ".phoshdebug installed (WLR_DRM_NO_ATOMIC=1, WLR_NO_HARDWARE_CURSORS=1)"

    # Force the phone-shaped portrait resolution (720x1440). The UTM display
    # (virtio-gpu-gl-pci) is configured by the host at 720x1440; if a live
    # Wayland session exists we additionally pin the output via wlr-randr so
    # Phosh is guaranteed to render at the target (guarded/non-fatal).
    if command -v wlr-randr >/dev/null 2>&1; then
        if [ -n "${WAYLAND_DISPLAY:-}" ] || [ -S "/run/user/${NUXEL_UID}/wayland-0" ]; then
            if wlr-randr >/dev/null 2>&1; then
                if wlr-randr --output "$(wlr-randr 2>/dev/null | awk '/^[A-Za-z]/{print $1; exit}')" \
                        --mode 720x1440 2>/dev/null; then
                    log_info "  wlr-randr: pinned output to 720x1440"
                else
                    log_warn "  wlr-randr could not set 720x1440 (no such mode?) — falling back to phosh-phone-resolution default"
                fi
            fi
        else
            log_info "  no live Wayland session at bootstrap — 720x1440 applied on next graphical boot via UTM display config"
        fi
    else
        log_warn "  wlr-randr not installed — resolution set via UTM display config (virtio-gpu-gl-pci @ 720x1440)"
    fi

    log_info "Phosh configured for mobile UX"
}
# ── Step 5a: Install Nuxel animated Plymouth boot theme ─────────────────
# Converts (or installs a pre-built copy of) the Nuxel boot animation MP4
# into a Plymouth "script" theme so the VM shows the actual Nuxel boot
# animation during startup instead of the generic Plymouth spinner.
#   - Prefer NUXEL_BOOT_THEME_TARBALL (host-generated, shipped by deploy-vm.sh
#     / build-vm-image.sh so the guest does not need ffmpeg/H.264 support).
#   - Prefer NUXEL_BOOT_THEME_DIR (an already-extracted theme dir).
#   - Fall back to building in-guest via tools/build-nuxel-boot-theme.sh when
#     ffmpeg is available.
install_nuxel_boot_theme() {
    local theme_dir="/usr/share/plymouth/themes/nuxel"
    local mp4="/usr/share/nuxel/boot/nuxel-boot-animation.mp4"
    local theme_source=""

    # Ensure the animation MP4 is present (normally copied earlier by
    # configure_phosh; this is defensive for standalone bootstrap runs).
    if [ ! -f "${mp4}" ] && [ -f "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4" ]; then
        mkdir -p /usr/share/nuxel/boot
        cp "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4" "${mp4}"
    fi

    if [ -n "${NUXEL_BOOT_THEME_TARBALL:-}" ] && [ -f "${NUXEL_BOOT_THEME_TARBALL}" ]; then
        theme_source="tarball"
    elif [ -n "${NUXEL_BOOT_THEME_DIR:-}" ] && [ -d "${NUXEL_BOOT_THEME_DIR}" ] \
        && [ -f "${NUXEL_BOOT_THEME_DIR}/nuxel.plymouth" ]; then
        theme_source="dir"
    elif [ -f "${mp4}" ] && [ -x "${NUXEL_ROOT}/tools/build-nuxel-boot-theme.sh" ] \
        && command -v ffmpeg >/dev/null 2>&1; then
        theme_source="build"
    fi

    if [ -z "${theme_source}" ]; then
        log_warn "Nuxel boot theme unavailable (no shipped frames and no in-guest ffmpeg); keeping default Plymouth theme"
        return 0
    fi

    mkdir -p "${theme_dir}"

    case "${theme_source}" in
        tarball)
            log_info "Installing Nuxel boot theme from ${NUXEL_BOOT_THEME_TARBALL}"
            tar -xzf "${NUXEL_BOOT_THEME_TARBALL}" -C "${theme_dir}"
            ;;
        dir)
            log_info "Installing Nuxel boot theme from ${NUXEL_BOOT_THEME_DIR}"
            cp -a "${NUXEL_BOOT_THEME_DIR}/." "${theme_dir}/"
            ;;
        build)
            log_info "Building Nuxel boot theme in-guest (ffmpeg)..."
            # Loop the animation until plymouthd quits (see NUXEL_BOOT_THEME_LOOP
            # in tools/build-nuxel-boot-theme.sh); a play-once theme freezes on
            # the last frame when boot outlasts the 8s clip, which reads as a hang.
            NUXEL_BOOT_THEME_LOOP=1 "${NUXEL_ROOT}/tools/build-nuxel-boot-theme.sh" \
                --mp4 "${mp4}" --width 720 --height 1440 --out "${theme_dir}"
            ;;
    esac

    # The theme may be shipped as a host-built tarball whose entries carry the
    # host uid/gid (and the extracted dir is often 0700). plymouthd reads it as
    # root, but plymouth-set-default-theme validates readability and SELinux
    # needs a sane context, so normalize ownership + perms now.
    chown -R root:root "${theme_dir}" 2>/dev/null || true
    chmod -R a+rX "${theme_dir}" 2>/dev/null || true

    if [ ! -f "${theme_dir}/nuxel.plymouth" ] || [ ! -f "${theme_dir}/nuxel.script" ]; then
        log_warn "Nuxel boot theme incomplete — keeping default Plymouth theme"
        return 0
    fi

    # Point Plymouth at the Nuxel theme.
    mkdir -p /etc/plymouth
    cat > /etc/plymouth/plymouthd.conf <<'CONFEOF'
[Daemon]
Theme=nuxel
ShowDelay=0
DeviceTimeout=10
CONFEOF

    if command -v plymouth-set-default-theme >/dev/null 2>&1; then
        if ! plymouth-set-default-theme nuxel; then
            log_warn "plymouth-set-default-theme nuxel failed — default theme may not be nuxel"
        fi
    fi

    # Debian/Ubuntu select the default theme via the default.plymouth alternative.
    if command -v update-alternatives >/dev/null 2>&1; then
        update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth \
            "${theme_dir}/nuxel.plymouth" 100 2>/dev/null || true
        update-alternatives --set default.plymouth "${theme_dir}/nuxel.plymouth" 2>/dev/null || true
    fi

    # Install a GRUB-friendly boot background (plain RGB PNG) so the graphical
    # GRUB stage shows the Nuxel splash the instant GRUB renders — before the
    # kernel/Plymouth takes over. Prefer the dedicated RGB background produced
    # by tools/build-nuxel-boot-theme.sh; fall back to the first frame.
    local grub_bg="/usr/share/nuxel/boot/nuxel-grub-background.png"
    mkdir -p "$(dirname "${grub_bg}")"
    if [ -f "${theme_dir}/nuxel-grub-background.png" ]; then
        cp -f "${theme_dir}/nuxel-grub-background.png" "${grub_bg}" 2>/dev/null || true
    elif [ -f "${theme_dir}/frame-0001.png" ]; then
        cp -f "${theme_dir}/frame-0001.png" "${grub_bg}" 2>/dev/null || true
    fi

    log_info "Nuxel Plymouth boot theme installed"
}

# ── Step 5a-bis: Install Plymouth handoff shim ──────────────────────────
# GDM calls `plymouth deactivate` the moment it starts managing displays,
# which drops DRM master and freezes the Nuxel boot animation while GDM then
# waits up to SEAT0_GRAPHICS_CHECK_TIMEOUT (10s) for udev to settle before it
# starts the Wayland compositor. On this VM virtio-gpu reports as a secondary
# PCI adapter (no boot_vga/boot_display sysfs attribute), so GDM always takes
# that 10s path. A tiny `/usr/local/bin/plymouth` shim (earlier on GDM's PATH)
# delays only the `deactivate` command until just before the compositor starts,
# keeping the animation spinning through the otherwise-frozen window.
install_nuxel_plymouth_handoff_shim() {
    log_info "Installing Nuxel Plymouth handoff shim..."

    local real_plymouth="/usr/bin/plymouth"
    [ -x "${real_plymouth}" ] || real_plymouth="$(command -v plymouth 2>/dev/null | head -1)"
    if [ -z "${real_plymouth}" ]; then
        log_warn "plymouth client binary not found -- skipping handoff shim"
        return 0
    fi

    mkdir -p /usr/local/bin
    cat > /usr/local/bin/plymouth <<'PLYMOUTH_SHIM'
#!/bin/sh
# Nuxel Plymouth handoff shim (installed by vm/nuxel-vm-bootstrap.sh).
#
# GDM invokes `plymouth deactivate` at display-manager startup, which freezes
# the boot animation well before GDM actually starts the Wayland compositor on
# this virtio-gpu VM. Delay the real deactivate until just before that handoff
# so the Nuxel boot animation keeps spinning until the desktop takes over.

REAL_PLYMOUTH="/usr/bin/plymouth"
[ -x "${REAL_PLYMOUTH}" ] || REAL_PLYMOUTH="/bin/plymouth"

# A primary GPU makes GDM proceed immediately (no 10s udev-settle wait), so
# there is nothing to delay in that case.
is_primary_gpu() {
    for card in /sys/class/drm/card*; do
        [ -e "$card" ] || continue
        if [ -r "$card/boot_display" ] && [ "$(cat "$card/boot_display" 2>/dev/null)" = "1" ]; then
            return 0
        fi
        pci="$(readlink -f "$card/device" 2>/dev/null)"
        if [ -n "$pci" ] && [ -r "$pci/boot_vga" ] && [ "$(cat "$pci/boot_vga" 2>/dev/null)" = "1" ]; then
            return 0
        fi
    done
    return 1
}

if [ "$1" = "deactivate" ]; then
    if is_primary_gpu; then
        exec "${REAL_PLYMOUTH}" deactivate
    fi
    # Return immediately so GDM does not block on this command; the real
    # deactivate is replayed in the background just before the display factory
    # starts the Wayland session (GDM's seat0 udev-settle window is 10s).
    (
        sleep "${NUXEL_PLYMOUTH_DEACTIVATE_DELAY:-9.5}"
        exec "${REAL_PLYMOUTH}" deactivate
    ) >/dev/null 2>&1 </dev/null &
    exit 0
fi

exec "${REAL_PLYMOUTH}" "$@"
PLYMOUTH_SHIM

    chmod 0755 /usr/local/bin/plymouth
    chown root:root /usr/local/bin/plymouth 2>/dev/null || true
    command -v restorecon >/dev/null 2>&1 && restorecon /usr/local/bin/plymouth 2>/dev/null || true

    log_info "Nuxel Plymouth handoff shim installed at /usr/local/bin/plymouth"
}

# ── Step 5b: Configure GRUB for quiet boot (systemd VM) ───────────

configure_grub_quiet_boot() {
    log_info "Configuring GRUB for quiet splash boot..."
    
    # Only apply to GRUB-based systems
    if ! command -v grub-mkconfig &>/dev/null && ! command -v grub2-mkconfig &>/dev/null; then
        log_warn "GRUB not found -- skipping GRUB quiet boot config"
        return 0
    fi
    
    local grub_cfg=""
    if [ -f /etc/default/grub ]; then
        grub_cfg="/etc/default/grub"
    elif [ -f /etc/sysconfig/grub ]; then
        grub_cfg="/etc/sysconfig/grub"
    else
        log_warn "No GRUB config file found"
        return 0
    fi
    
    log_info "Configuring ${grub_cfg} for quiet splash..."
    
    # Set timeout style
    if grep -q "^GRUB_TIMEOUT_STYLE=" "${grub_cfg}"; then
        sed -i "s/^GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=hidden/" "${grub_cfg}"
    else
        echo "GRUB_TIMEOUT_STYLE=hidden" >> "${grub_cfg}"
    fi
    
    # Set timeout to 0 for instant boot
    if grep -q "^GRUB_TIMEOUT=" "${grub_cfg}"; then
        sed -i "s/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=0/" "${grub_cfg}"
    else
        echo "GRUB_TIMEOUT=0" >> "${grub_cfg}"
    fi
    
    # Add quiet splash to kernel cmdline.
    # The ARM `virt` machine always exposes a PL011 UART, and QEMU's SPCR/DTB
    # makes ttyAMA0 the *only* active kernel console. When Plymouth sees only a
    # serial console it forces the text/details splash onto that serial console
    # and never renders on virtio-gpu, leaving the UTM display black ("Display
    # output is not active") until GDM.
    #   * console=tty0 forces a graphical (fbcon) console and overrides the
    #     device-tree serial console, so /sys/class/tty/console/active is a VT
    #     rather than ttyAMA0.
    #   * plymouth.ignore-serial-consoles + plymouth.graphical belt-and-braces
    #     make plymouthd use the DRM renderer on virtio-gpu regardless.
    # video=720x1440 pins the virtio-gpu framebuffer mode (the UTM display is
    # 720x1440), and rd.driver.pre=virtio_gpu loads the virtio-gpu KMS driver
    # early in the initramfs so /dev/dri/card0 exists for the initramfs
    # Plymouth splash.
    local boot_args="quiet splash plymouth.ignore-serial-consoles plymouth.graphical console=tty0 loglevel=3 rd.driver.pre=virtio_gpu video=720x1440"
    if grep -q "^GRUB_CMDLINE_LINUX_DEFAULT=" "${grub_cfg}"; then
        sed -i "s/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT=\"${boot_args}\"/" "${grub_cfg}"
    else
        echo "GRUB_CMDLINE_LINUX_DEFAULT=\"${boot_args}\"" >> "${grub_cfg}"
    fi

    # Route GRUB to the graphical framebuffer (gfxterm) so the UTM display
    # becomes active the moment GRUB runs — closing the "Display output is not
    # active" window during the UEFI→kernel handover.
    if grep -q "^GRUB_TERMINAL_OUTPUT=" "${grub_cfg}"; then
        sed -i 's/^GRUB_TERMINAL_OUTPUT=.*/GRUB_TERMINAL_OUTPUT="gfxterm"/' "${grub_cfg}"
    else
        echo 'GRUB_TERMINAL_OUTPUT="gfxterm"' >> "${grub_cfg}"
    fi
    if grep -q "^GRUB_TERMINAL_INPUT=" "${grub_cfg}"; then
        sed -i 's/^GRUB_TERMINAL_INPUT=.*/GRUB_TERMINAL_INPUT="console"/' "${grub_cfg}"
    else
        echo 'GRUB_TERMINAL_INPUT="console"' >> "${grub_cfg}"
    fi

    # Show the Nuxel background behind a hidden, instant menu, and keep the
    # framebuffer alive across the GRUB→kernel handover so there is no blank
    # gap before Plymouth renders.
    if grep -q "^GRUB_GFXMODE=" "${grub_cfg}"; then
        sed -i 's/^GRUB_GFXMODE=.*/GRUB_GFXMODE="720x1440x32,1280x800x32,auto"/' "${grub_cfg}"
    else
        echo 'GRUB_GFXMODE="720x1440x32,1280x800x32,auto"' >> "${grub_cfg}"
    fi
    if grep -q "^GRUB_GFXPAYLOAD_LINUX=" "${grub_cfg}"; then
        sed -i 's/^GRUB_GFXPAYLOAD_LINUX=.*/GRUB_GFXPAYLOAD_LINUX="keep"/' "${grub_cfg}"
    else
        echo 'GRUB_GFXPAYLOAD_LINUX="keep"' >> "${grub_cfg}"
    fi
    if grep -q "^GRUB_BACKGROUND=" "${grub_cfg}"; then
        sed -i 's#^GRUB_BACKGROUND=.*#GRUB_BACKGROUND="/usr/share/nuxel/boot/nuxel-grub-background.png"#' "${grub_cfg}"
    else
        echo 'GRUB_BACKGROUND="/usr/share/nuxel/boot/nuxel-grub-background.png"' >> "${grub_cfg}"
    fi

    # Ensure the PNG reader module is preloaded so background_image works on
    # every GRUB build (Fedora ships png.mod in grub2-efi).
    if grep -q "^GRUB_PRELOAD_MODULES=" "${grub_cfg}"; then
        if ! grep -q '^GRUB_PRELOAD_MODULES=.*png' "${grub_cfg}"; then
            sed -i 's/^GRUB_PRELOAD_MODULES=\(.*\)/GRUB_PRELOAD_MODULES=\1 png/' "${grub_cfg}"
        fi
    else
        echo 'GRUB_PRELOAD_MODULES="png"' >> "${grub_cfg}"
    fi

    
    # Install Plymouth if not present
    if ! command -v plymouthd &>/dev/null; then
        log_info "Installing Plymouth..."
        case "${DISTRO_ID}" in
            fedora)
                dnf install -y plymouth plymouth-plugin-script 2>/dev/null || log_warn "dnf plymouth install failed (exit $?)"
                ;;
            debian|ubuntu)
                apt-get install -y plymouth plymouth-script plymouth-themes 2>/dev/null || log_warn "apt plymouth install failed (exit $?)"
                ;;
        esac
    fi
    
    # Install the animated Nuxel Plymouth boot theme (or keep the default
    # spinner if the theme cannot be built/obtained in this environment).
    install_nuxel_boot_theme

    # Keep that animation spinning until GDM is actually ready to hand the
    # display to the compositor (rather than freezing it at GDM startup).
    install_nuxel_plymouth_handoff_shim
    
    # Regenerate GRUB config
    log_info "Regenerating GRUB config..."
    if command -v grub-mkconfig &>/dev/null; then
        grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true
    elif command -v grub2-mkconfig &>/dev/null; then
        grub2-mkconfig -o /boot/grub2/grub.cfg 2>/dev/null || true
    fi
    
    # Regenerate initramfs (to include Plymouth + the nuxel theme)
    if command -v dracut &>/dev/null; then
        dracut --force --regenerate-all 2>/dev/null || log_warn "dracut initramfs rebuild failed (exit $?)"
        # Confirm the nuxel theme actually made it into the initramfs; without
        # it the early (initramfs) splash phase falls back to the default.
        if command -v lsinitrd >/dev/null 2>&1 && lsinitrd 2>/dev/null | grep -q "themes/nuxel"; then
            log_info "Nuxel boot theme verified inside initramfs"
        else
            log_warn "Nuxel boot theme NOT found in initramfs — early splash may not show"
        fi
    elif command -v update-initramfs &>/dev/null; then
        update-initramfs -u 2>/dev/null || log_warn "update-initramfs failed (exit $?)"
    fi
    
    log_info "GRUB quiet splash configured (reboot to see effect)"
}

# ── Step 6: Enable Services ───────────────────────────────────────────────

enable_services() {
    log_info "Enabling Nuxel services..."

    systemctl enable nuxel-bridge.service 2>/dev/null || true
    systemctl enable nuxel-http-bridge.service 2>/dev/null || true
    systemctl enable nuxel-portal.service 2>/dev/null || true
    systemctl enable nuxel-notifications.service 2>/dev/null || true
    systemctl enable nuxel-web.service 2>/dev/null || true

    # Install and enable PWA web server (port 8000)
    if [ -f "${NUXEL_ROOT}/services/nuxel-web.service" ]; then
        cp "${NUXEL_ROOT}/services/nuxel-web.service" /etc/systemd/system/nuxel-web.service
        systemctl daemon-reload
        systemctl enable --now nuxel-web.service 2>/dev/null || true
        log_info "nuxel-web.service enabled (port 8000)"
    fi

    # Start services. `systemctl restart dbus` drops EVERY D-Bus client
    # connection (gdm, systemd-logind, the user session) — observed in the
    # 2026-08-19 UTM guest: it wedges logind session creation
    # ("Transport endpoint is not connected" on session scopes) and puts GDM
    # into an autologin crash loop (gdm-session-worker abort:
    # set_up_for_new_vt: assertion failed (session_vt > 0)). It is therefore
    # ONLY issued when no display manager is active (e.g. headless first
    # bootstrap before gdm comes up). With a live desktop the system bus
    # already has the nuxel policies loaded; the nuxel services are restarted
    # below so they bind fresh bus connections.
    if ! systemctl is-active --quiet gdm.service 2>/dev/null \
       && ! systemctl is-active --quiet display-manager.service 2>/dev/null; then
        systemctl restart dbus 2>/dev/null || true
    else
        log_info "Display manager active — skipping 'systemctl restart dbus' (would crash the graphical session); nuxel D-Bus policies already loaded."
    fi
    systemctl restart nuxel-bridge.service 2>/dev/null || true
    systemctl restart nuxel-portal.service 2>/dev/null || true
    systemctl restart nuxel-notifications.service 2>/dev/null || true
    # nuxel-http-bridge is Type=simple (no bus-tracking auto-restart), so
    # without an explicit restart it keeps a stale SystemBus connection and
    # every bridge RPC fails with org.freedesktop.DBus.Error.Disconnected
    # (the api.py dbus-error path). Restarting also guarantees the API is
    # actually STARTED on a fresh bootstrap (enable alone never starts a
    # Type=simple unit). nuxel-web is restarted for the same consistency.
    systemctl restart nuxel-http-bridge.service 2>/dev/null || true
    systemctl restart nuxel-web.service 2>/dev/null || true

    log_info "All services enabled and started"
}

# ── Step 6b: Prepare First-Boot Marker ─────────────────────────────────────

prepare_firstboot_marker() {
    log_info "Preparing first-boot marker..."

    # Canonical marker (from configs/nuxel/paths.conf):
    #   NUXEL_FIRSTBOOT_MARKER=/var/lib/nuxel/.firstboot-complete
    # The marker is /var/lib/nuxel/.firstboot-complete (single source of truth
    # for the VM/repo path, NOT /etc/nuxel which is OpenRC-only for a different
    # target). We ensure the parent dir exists and write the completed marker
    # so the wizard/agent treat the VM as already first-booted.
    #
    # Preserve a .pending-firstboot sentinel too so the OpenRC-firstboot unit,
    # if ever present, still sees the reconciliation root we created.
    mkdir -p "${NUXEL_DATA_DIR}"
    chmod 770 "${NUXEL_DATA_DIR}"
    chown "${NUXEL_USER}:${NUXEL_USER}" "${NUXEL_DATA_DIR}" 2>/dev/null || true

    local marker="${NUXEL_DATA_DIR}/.firstboot-complete"
    local marker_sentinel="${NUXEL_DATA_DIR}/.pending-firstboot"

    # Write the canonical completed marker (briq Step 6b) idempotently.
    if [ ! -f "${marker}" ]; then
        : > "${marker}" 2>/dev/null && log_info "  wrote ${marker}"             || log_warn "  could not write ${marker}"
    else
        log_info "  ${marker} already present (idempotent re-run)"
    fi
    chown "${NUXEL_USER}:${NUXEL_USER}" "${marker}" 2>/dev/null || true

    # Keep the reconciliation sentinel as well.
    : > "${marker_sentinel}" 2>/dev/null || true
    chown "${NUXEL_USER}:${NUXEL_USER}" "${marker_sentinel}" 2>/dev/null || true

    if [ -f "${marker}" ]; then
        log_info "  first-boot marker ready: ${marker}"
    else
        log_warn "  could not write first-boot marker under ${NUXEL_DATA_DIR}"
    fi
}

# ── Step 7: Verify Installation ───────────────────────────────────────────

verify_installation() {
    log_info "Verifying installed Nuxel services..."
    local rc=0
    local unit
    check_phosh
    # NUXEL_VERIFY=0 skips the active-check (muted), default is to verify.
    if [ "${NUXEL_VERIFY:-1}" = "0" ]; then
        log_warn "NUXEL_VERIFY=0 -- skipping service verification"
        return 0
    fi

    for unit in nuxel-bridge.service nuxel-portal.service \
                nuxel-notifications.service nuxel-http-bridge.service nuxel-web.service; do
        if systemctl is-active --quiet "${unit}" 2>/dev/null; then
            log_info "  [OK] ${unit} is active"
        elif systemctl is-enabled --quiet "${unit}" 2>/dev/null; then
            log_warn "  [WARN] ${unit} enabled but not yet active (restart after boot)"
            rc=$((rc + 1))
        else
            log_warn "  [WARN] ${unit} unit file present (enable it manually)"
            rc=$((rc + 1))
        fi
    done

    # Portal D-Bus Ping (briq-v1): org.nuxel.Portal.Ping must respond.
    if command -v gdbus &>/dev/null && systemctl is-active --quiet nuxel-portal.service 2>/dev/null; then
        local ping_out
        ping_out=$(gdbus call --system --dest org.nuxel.Portal \
            --object-path /org/nuxel/Portal --method org.nuxel.Portal.Ping "smoke" 2>/dev/null) || ping_out=""
        if [ -n "${ping_out}" ]; then
            log_info "  [OK] org.nuxel.Portal.Ping -> ${ping_out}"
        else
            log_warn "  [WARN] org.nuxel.Portal.Ping did not respond"
            rc=$((rc + 1))
        fi
    else
        log_warn "  [WARN] portal Ping skipped (gdbus or portal not running yet)"
    fi

    # HTTP API -> Bridge -> D-Bus round trip (audit briq-12: never accept a
    # mock/fallback body as proof of a live bridge). /api/v1/ping is routed by
    # nuxel-http-bridge (api.py) through org.nuxel.Bridge.Ping over the system
    # bus; a 200 with '"status": "ok"' and '"service": "nuxel-bridge"' proves
    # the real bridge answered. Any dbus-error / failure body increments rc.
    if command -v curl >/dev/null 2>&1 && systemctl is-active --quiet nuxel-http-bridge.service 2>/dev/null; then
        local health ping_body ping_ok
        health=$(curl -s -m 5 http://127.0.0.1:8080/api/v1/health 2>/dev/null) || health=""
        if printf '%s' "${health}" | grep -q '"success": *true'; then
            log_info "  [OK] HTTP /api/v1/health -> ${health}"
        else
            log_warn "  [WARN] HTTP /api/v1/health not OK: ${health}"
            rc=$((rc + 1))
        fi
        local token
        token=$(curl -s -m 5 -X POST http://127.0.0.1:8080/api/v1/auth/token \
            -H 'Content-Type: application/json' -d '{"app_id":"bootstrap-verify"}' 2>/dev/null \
            | sed -n 's/.*"token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
        if [ -n "${token}" ]; then
            ping_body=$(curl -s -m 8 -H "Authorization: Bearer ${token}" \
                "http://127.0.0.1:8080/api/v1/ping?message=bootstrap" 2>/dev/null) || ping_body=""
            ping_ok=$(printf '%s' "${ping_body}" | grep -c '"status"[[:space:]]*:[[:space:]]*"ok"')
            if [ "${ping_ok}" -ge 1 ] && printf '%s' "${ping_body}" | grep -q '"service"[[:space:]]*:[[:space:]]*"nuxel-bridge"'; then
                log_info "  [OK] HTTP /api/v1/ping round-trips through real bridge -> ${ping_body}"
            else
                log_warn "  [WARN] HTTP /api/v1/ping did NOT round-trip through the real bridge: ${ping_body}"
                rc=$((rc + 1))
            fi
        else
            log_warn "  [WARN] could not obtain API session token — skipping ping round-trip"
            rc=$((rc + 1))
        fi
    else
        log_warn "  [WARN] HTTP bridge round-trip skipped (curl or nuxel-http-bridge not available)"
    fi

    if [ "${rc}" -eq 0 ]; then
        log_info "All Nuxel services verified."
    else
        log_warn "Some services need a reboot to become active (expected on first boot)."
        log_warn "Run: ./ci/phase3-smoke-vm.sh after reboot to confirm."
    fi
    return 0
}

# ── Main ──────────────────────────────────────────────────────────────────


main() {
    echo ""
    echo "=============================================="
    echo "  Nuxel VM Bootstrap Script"
    echo "  Target: aarch64 UTM VM"
    echo "=============================================="
    echo ""

    check_root
    detect_distro
    if [ -d "${NUXEL_ROOT}/services" ] && [ -d "${NUXEL_ROOT}/configs" ]; then
        log_info "NUXEL_ROOT resolves to ${NUXEL_ROOT} (repo sources staged)"
    else
        log_warn "NUXEL_ROOT=${NUXEL_ROOT} has no services/configs — using embedded fallbacks."
        log_warn "Stage the repo in the VM (see vm/utm-setup-guide.md) for full config install."
    fi

    echo ""
    echo "─── Step 0: Install Prerequisites ───"
    install_prerequisites

    # Flatpak runtime (network-fallback per briq-4) right after prerequisites.
    install_flatpak_runtime

    echo ""
    echo "─── Step 1: Create nuxel User ───"
    create_nuxel_user
    create_service_users

    echo ""
    echo "─── Step 2: Create Directory Layout ───"
    create_directory_layout

    echo ""
    echo "─── Step 3: Install Core Services ───"
    install_nuxel_bridge
    install_nuxel_http_bridge
    install_nuxel_portal
    install_nuxel_notifications
    install_dbus_policy
    create_python_venv

    echo ""
    echo "─── Step 4: Hardened Configs ───"
    install_apparmor_profiles
    install_hardened_malloc
    install_nftables_rules
    install_security_hardening

    echo ""
    echo "─── Step 5: Configure Phosh ───"
    configure_phosh
    configure_grub_quiet_boot

    echo ""
    echo "─── Step 6: Enable Services ───"
    enable_services

    echo ""
    echo "─── Step 6b: Prepare First-Boot Marker ───"
    prepare_firstboot_marker

    echo ""
    echo "─── Step 7: Verify Installation ───"
    verify_installation || true

    echo ""
    echo "=============================================="
    echo -e "${GREEN}  Nuxel VM bootstrap complete!${NC}"
    echo ""
    echo "  What to do next:"
    echo "  1. Reboot the VM:  sudo reboot"
    echo "  2. Verify Phosh launches at phone resolution"
    echo "  3. Check services: sudo systemctl status nuxel-*"
    echo "  4. Run the sandbox tests"
    echo "  5. Take a UTM snapshot for rollback safety"
    echo ""
    echo "  For UTM snapshot management, use:"
    echo "    ./vm/nuxel-vm-snapshot.sh"
    echo "=============================================="
}

main "$@"
