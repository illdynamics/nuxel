#!/bin/bash
# Nuxel Immutable Root Filesystem Builder
#
# Builds the root filesystem from Flatpak runtime (org.gnome.Platform//46)
# plus Nuxel-specific overlay. Creates a dm-verity protected system image.
#
# No package manager in the final image.
# All apps installed as Flatpak bundles in /var/lib/flatpak.
#
# Output: build/out/system.img (+ system.img.verity hash tree)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

NUXEL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_OUT="${NUXEL_ROOT}/build/out"
ROOTFS_DIR="${BUILD_OUT}/rootfs"
SYSTEM_IMG="${BUILD_OUT}/system.img"
SYSTEM_IMG_SIZE_MB=4096  # Default 4GB, will be resized

# Init-system selection (briq-21): the rootfs builder defaults to
# systemd for the Fedora/UVM VM target, but honors an explicit override to
# build an OpenRC image for the Alpine/pmOS mustang target. All systemd unit
# installs are gated on NUXEL_INIT=systemd; when NUXEL_INIT=openrc the OpenRC
# scripts under shell/config/openrc are installed instead.
export NUXEL_INIT="${NUXEL_INIT:-systemd}"

# S10+ must never re-use the host-architecture Flatpak fallback. A complete
# Fedora ARM64 PHONE runtime is built from RPMs instead.
# This is intentionally fail-closed; see images/s10plus/build-phone-rootfs-fedora.sh.
if [ "${NUXEL_DEVICE:-}" = s10plus ]; then
    echo '[nuxel][error] S10+ phone rootfs cannot be built from a host Flatpak runtime.' >&2
    echo '[nuxel][error] Run: bash images/s10plus/build-phone-rootfs-fedora.sh' >&2
    exit 2
fi

# Clean build directory
clean() {
    log_info "Cleaning build directory..."
    rm -rf "$ROOTFS_DIR"
    mkdir -p "$ROOTFS_DIR" "$BUILD_OUT"
    log_ok "Clean complete"
}

# Step 1: Extract Flatpak runtime as base layer
install_flatpak_base() {
    log_info "[1/6] Installing Flatpak runtime base..."
    
    local runtime="org.gnome.Platform//46"
    
    # Ensure Flatpak runtime is installed
    if ! flatpak list --system 2>/dev/null | grep -q "org.gnome.Platform.*46"; then
        log_info "Installing ${runtime} (this may take a while)..."
        flatpak install --system --noninteractive "$runtime" 2>/dev/null || {
            log_warn "Flatpak runtime install failed. Attempting alternative approach..."
            log_warn "You may need to: flatpak install --system org.gnome.Platform//46"
        }
    fi
    
    # Find the runtime deployment directory
    local runtime_dir
    runtime_dir=$(flatpak info --show-location "$runtime" 2>/dev/null || echo "")
    
    if [ -n "$runtime_dir" ] && [ -d "${runtime_dir}/files" ]; then
        log_info "Extracting runtime from ${runtime_dir}/files..."
        rsync -aHAX "${runtime_dir}/files/" "$ROOTFS_DIR/"
        log_ok "Flatpak runtime extracted"
    else
        log_warn "Cannot find Flatpak runtime installation."
        log_warn "Creating minimal rootfs structure..."
        
        # Create minimal directory structure
        mkdir -p "$ROOTFS_DIR"/{usr/{bin,lib,share},etc,var/{app,lib,log,tmp},dev,proc,sys,run,tmp}
        ln -sf /var/home "$ROOTFS_DIR/home"
        
        # Copy essential system libraries from host (cross-compile target)
        if [ -d /usr/aarch64-linux-gnu ]; then
            rsync -aHAX /usr/aarch64-linux-gnu/lib/ "$ROOTFS_DIR/usr/lib/" 2>/dev/null || true
        fi
    fi
    
    log_ok "Base runtime installed"
}

# Step 2: Install Nuxel core services
install_core_services() {
    log_info "[2/7] Installing Nuxel core services..."
    
    # nuxel-bridge
    install -Dm755 "${NUXEL_ROOT}/services/nuxel-bridge/src/bridge.py" \
        "${ROOTFS_DIR}/usr/bin/nuxel-bridge"
    install -Dm644 "${NUXEL_ROOT}/services/nuxel-bridge/src/api.py" \
        "${ROOTFS_DIR}/usr/lib/nuxel/bridge/api.py"
    install -Dm644 "${NUXEL_ROOT}/services/nuxel-bridge/src/capabilities.py" \
        "${ROOTFS_DIR}/usr/lib/nuxel/bridge/capabilities.py"
    
    if [ -f "${NUXEL_ROOT}/services/nuxel-bridge/dbus/org.nuxel.Bridge.conf" ]; then
        install -Dm644 "${NUXEL_ROOT}/services/nuxel-bridge/dbus/org.nuxel.Bridge.conf" \
            "${ROOTFS_DIR}/etc/dbus-1/system.d/org.nuxel.Bridge.conf"
    fi
    
    # nuxel-portal
    if [ -f "${NUXEL_ROOT}/services/nuxel-portal/src/portal.py" ]; then
        install -Dm755 "${NUXEL_ROOT}/services/nuxel-portal/src/portal.py" \
            "${ROOTFS_DIR}/usr/bin/nuxel-portal"
    fi
    if [ -f "${NUXEL_ROOT}/services/nuxel-portal/dbus/org.nuxel.Portal.conf" ]; then
        install -Dm644 "${NUXEL_ROOT}/services/nuxel-portal/dbus/org.nuxel.Portal.conf" \
            "${ROOTFS_DIR}/etc/dbus-1/system.d/org.nuxel.Portal.conf"
    fi
    
    # nuxel-notifications
    install -Dm755 "${NUXEL_ROOT}/services/nuxel-notifications/src/notifications.py" \
        "${ROOTFS_DIR}/usr/bin/nuxel-notifications"
    if [ -f "${NUXEL_ROOT}/services/nuxel-notifications/dbus/org.nuxel.Notifications.conf" ]; then
        install -Dm644 "${NUXEL_ROOT}/services/nuxel-notifications/dbus/org.nuxel.Notifications.conf" \
            "${ROOTFS_DIR}/etc/dbus-1/system.d/org.nuxel.Notifications.conf"
    fi
    
    # Init files (briq-21): systemd units for the VM target, OpenRC scripts
    # for the mustang/Alpine-pmOS target. Only the selected init system's
    # files are installed into the rootfs.
    if [ x"${NUXEL_INIT}" = xsystemd ]; then
        # systemd runtime/unit files
        if [ -f "${NUXEL_ROOT}/services/nuxel-bridge/systemd/nuxel-bridge.service" ]; then
            install -Dm644 "${NUXEL_ROOT}/services/nuxel-bridge/systemd/nuxel-bridge.service" \
                "${ROOTFS_DIR}/usr/lib/systemd/system/nuxel-bridge.service"
        fi
        if [ -f "${NUXEL_ROOT}/services/nuxel-bridge/polkit/50-nuxel-bridge-network.rules" ]; then
            install -Dm644 "${NUXEL_ROOT}/services/nuxel-bridge/polkit/50-nuxel-bridge-network.rules" \
                "${ROOTFS_DIR}/etc/polkit-1/rules.d/50-nuxel-bridge-network.rules"
        fi
        if [ -f "${NUXEL_ROOT}/services/nuxel-portal/systemd/nuxel-portal.service" ]; then
            install -Dm644 "${NUXEL_ROOT}/services/nuxel-portal/systemd/nuxel-portal.service" \
                "${ROOTFS_DIR}/usr/lib/systemd/system/nuxel-portal.service"
        fi
        if [ -f "${NUXEL_ROOT}/services/nuxel-notifications/systemd/nuxel-notifications.service" ]; then
            install -Dm644 "${NUXEL_ROOT}/services/nuxel-notifications/systemd/nuxel-notifications.service" \
                "${ROOTFS_DIR}/usr/lib/systemd/system/nuxel-notifications.service"
        fi
        # nuxel-web (PWA static server, port 8000)
        if [ -f "${NUXEL_ROOT}/services/nuxel-web.service" ]; then
            install -Dm644 "${NUXEL_ROOT}/services/nuxel-web.service"             "${ROOTFS_DIR}/usr/lib/systemd/system/nuxel-web.service"
            log_info "  ✓ nuxel-web.service (systemd)"
        fi
        log_info "  ✓ systemd units installed (NUXEL_INIT=systemd)"
    elif [ x"${NUXEL_INIT}" = xopenrc ]; then
        mkdir -p "${ROOTFS_DIR}/etc/init.d"
        for script in "${NUXEL_ROOT}/shell/config/openrc"/nuxel-*; do
            [ -f "$script" ] || continue
            install -Dm755 "$script" "${ROOTFS_DIR}/etc/init.d/$(basename "$script")"
        done
        log_info "  ✓ OpenRC scripts installed to /etc/init.d (NUXEL_INIT=openrc)"
    else
        log_warn "  ✗ Unknown NUXEL_INIT='${NUXEL_INIT}' — no init files installed"
    fi
    
    log_ok "Core services installed"
}

# Step 3: Install native GTK4 apps
install_native_apps() {
    log_info "[3/7] Installing native apps..."
    
    # Build directory for compiled native apps
    local app_build_dir="${NUXEL_ROOT}/build/native-apps"
    mkdir -p "${ROOTFS_DIR}/usr/bin"
    
    # Try to compile native apps, fall back to prebuilt or source install
    for app in dialer messages contacts settings permissions; do
        app_binary="nuxel-${app}"
        app_src="${NUXEL_ROOT}/shell/nuxel-shell/nuxel-${app}/main.c"
        prebuilt_bin="${app_build_dir}/${app_binary}"
        
        if [ -f "${prebuilt_bin}" ]; then
            # Prebuilt binary exists — install it
            log_info "Installing ${app_binary} (prebuilt)..."
            install -Dm755 "${prebuilt_bin}" "${ROOTFS_DIR}/usr/bin/${app_binary}"
        elif [ -f "$app_src" ] && command -v gcc &>/dev/null && pkg-config --exists gtk4 libadwaita-1 2>/dev/null; then
            # Try to compile on the fly
            log_info "Compiling ${app_binary} from source..."
            # pkg-config flags are intentionally word-split into multiple gcc args.
            # shellcheck disable=SC2046
            gcc -O2 -Wall                 $(pkg-config --cflags gtk4 libadwaita-1)                 "$app_src" -o "${app_build_dir}/${app_binary}"                 $(pkg-config --libs gtk4 libadwaita-1) 2>/dev/null && {
                install -Dm755 "${app_build_dir}/${app_binary}" "${ROOTFS_DIR}/usr/bin/${app_binary}"
                log_info "  ✓ ${app_binary} compiled and installed"
            } || {
                log_warn "  ✗ ${app_binary} compilation failed — installing source for later build"
                install -Dm644 "$app_src" "${ROOTFS_DIR}/usr/src/nuxel/${app_binary}/main.c"
            }
        elif [ -f "$app_src" ]; then
            # No compiler available — install source for later build
            log_warn "${app_binary}: no compiler or GTK4 dev libs — installing source only"
            install -Dm644 "$app_src" "${ROOTFS_DIR}/usr/src/nuxel/${app_binary}/main.c"
        else
            log_warn "${app_binary}: no source found"
        fi
        
        # Install .desktop file (always)
        desktop_src="${NUXEL_ROOT}/shell/config/nuxel-${app}.desktop"
        if [ -f "$desktop_src" ]; then
            install -Dm644 "$desktop_src"                 "${ROOTFS_DIR}/usr/share/applications/nuxel-${app}.desktop"
        fi
        
        # Install icon (always)
        icon_src="${NUXEL_ROOT}/shell/config/icons/${app}.svg"
        if [ -f "$icon_src" ]; then
            install -Dm644 "$icon_src"                 "${ROOTFS_DIR}/usr/share/icons/hicolor/scalable/apps/nuxel-${app}.svg"
        fi
    done
    
    # firstboot wizard (Python, no compilation needed)
    local firstboot_src="${NUXEL_ROOT}/shell/nuxel-shell/nuxel-firstboot/main.py"
    if [ -f "$firstboot_src" ]; then
        install -Dm755 "$firstboot_src" "${ROOTFS_DIR}/usr/bin/nuxel-firstboot"
        log_info "  ✓ nuxel-firstboot installed"
    fi
    
    # PWA launcher
    local launcher_src="${NUXEL_ROOT}/pwa/launcher/nuxel-pwa-launcher.c"
    local launcher_bin="${NUXEL_ROOT}/build/native-apps/nuxel-pwa-launcher"
    if [ -f "${launcher_bin}" ]; then
        install -Dm755 "${launcher_bin}" "${ROOTFS_DIR}/usr/bin/nuxel-pwa-launcher"
        log_info "  ✓ nuxel-pwa-launcher (prebuilt)"
    elif [ -f "$launcher_src" ] && command -v gcc &>/dev/null && pkg-config --exists webkitgtk-6.0 2>/dev/null; then
        # pkg-config flags are intentionally word-split into multiple gcc args.
        # shellcheck disable=SC2046
        gcc -O2 -Wall             $(pkg-config --cflags webkitgtk-6.0 gtk4)             "$launcher_src" -o "${launcher_bin}"             $(pkg-config --libs webkitgtk-6.0 gtk4) 2>/dev/null && {
            install -Dm755 "${launcher_bin}" "${ROOTFS_DIR}/usr/bin/nuxel-pwa-launcher"
            log_info "  ✓ nuxel-pwa-launcher compiled"
        }
    fi
    
    # GSettings schema
    schema_src="${NUXEL_ROOT}/shell/config/schemas/org.nuxel.settings.gschema.xml"
    if [ -f "$schema_src" ]; then
        install -Dm644 "$schema_src"             "${ROOTFS_DIR}/usr/share/glib-2.0/schemas/org.nuxel.settings.gschema.xml"
    fi
    
    # Phosh config
    phosh_override="${NUXEL_ROOT}/shell/config/phosh/nuxel-phosh-override.ini"
    if [ -f "$phosh_override" ]; then
        install -Dm644 "$phosh_override"             "${ROOTFS_DIR}/etc/phosh/phosh.ini"
    fi
    
    # Nuxel Home kiosk launcher
    if [ -f "${NUXEL_ROOT}/shell/nuxel-kiosk/nuxel-home-kiosk" ]; then
        install -Dm755 "${NUXEL_ROOT}/shell/nuxel-kiosk/nuxel-home-kiosk"             "${ROOTFS_DIR}/usr/bin/nuxel-home-kiosk"
        log_info "  ✓ nuxel-home-kiosk"
    fi
    
    # Nuxel Home desktop entry (for Phosh app drawer)
    if [ -f "${NUXEL_ROOT}/shell/config/nuxel-home.desktop" ]; then
        install -Dm644 "${NUXEL_ROOT}/shell/config/nuxel-home.desktop"             "${ROOTFS_DIR}/usr/share/applications/nuxel-home.desktop"
        log_info "  ✓ nuxel-home.desktop"
    fi
    
    # Nuxel Home kiosk systemd user service (auto-launch after login).
    # systemd-only (briq-21); skipped on the OpenRC/mustang target.
    if [ x"${NUXEL_INIT}" = xsystemd ] && [ -f "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-home-kiosk.service" ]; then
        install -Dm644 "${NUXEL_ROOT}/shell/config/systemd-user/nuxel-home-kiosk.service"             "${ROOTFS_DIR}/usr/lib/systemd/user/nuxel-home-kiosk.service"
        log_info "  ✓ nuxel-home-kiosk.service (user, systemd)"
    fi
    
    log_ok "Native apps installed"
}
# Step 4: Install security configs
install_security_configs() {
    log_info "[4/7] Installing security configs..."
    
    # hardened_malloc config
    mkdir -p "${ROOTFS_DIR}/etc"
    cat > "${ROOTFS_DIR}/etc/hardened-malloc.conf" << 'MALLOC'
zero_on_free = true
canary = true
guard_slabs = true
quarantine = true
quarantine_size = 16
large_config = true
handle_oom = abort
random_slab_selection = true
write_protect_metadata = true
large_guard_size = 65536
MALLOC
    
    # LD_PRELOAD for hardened_malloc
    cat > "${ROOTFS_DIR}/etc/ld.so.preload" << 'PRELOAD'
/usr/lib/libhardened_malloc.so
PRELOAD
    
    # AppArmor profiles
    mkdir -p "${ROOTFS_DIR}/etc/apparmor.d"
    if [ -d "${NUXEL_ROOT}/configs/apparmor.d" ]; then
        for profile in "${NUXEL_ROOT}"/configs/apparmor.d/*; do
            if [ -f "$profile" ]; then
                install -Dm644 "$profile" \
                    "${ROOTFS_DIR}/etc/apparmor.d/$(basename "$profile")"
            fi
        done
    fi
    
    # nftables firewall rules
    mkdir -p "${ROOTFS_DIR}/usr/share/nftables.d"
    if [ -f "${NUXEL_ROOT}/configs/nftables/nuxel-app-firewall.nft" ]; then
        install -Dm644 "${NUXEL_ROOT}/configs/nftables/nuxel-app-firewall.nft" \
            "${ROOTFS_DIR}/usr/share/nftables.d/nuxel-app-firewall.nft"
    fi
    
    # Sysctl hardening
    mkdir -p "${ROOTFS_DIR}/etc/sysctl.d"
    cat > "${ROOTFS_DIR}/etc/sysctl.d/99-nuxel-hardening.conf" << 'SYSCTL'
# Kernel hardening for Nuxel
kernel.kptr_restrict=2
kernel.dmesg_restrict=1
kernel.perf_event_paranoid=3
kernel.randomize_va_space=2
kernel.unprivileged_bpf_disabled=1
net.core.bpf_jit_harden=2
kernel.kexec_load_disabled=1
kernel.sysrq=0
kernel.yama.ptrace_scope=2
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.default.rp_filter=1
net.ipv4.tcp_syncookies=1
net.ipv4.tcp_rfc1337=1
SYSCTL
    
    log_ok "Security configs installed"
}


# Step 4.5: Install Nuxel assets (wallpaper, boot animation)
install_assets() {
    log_info "[4.5/7] Installing Nuxel assets..."

    # Populate the per-PWA asset copies from the single source-of-truth
    # assets/ tree (briq-23). This runs before PWA packaging so every app's
    # ./assets/nuxel-background.png reference resolves without the duplicates
    # being checked in.
    if [ -x "${NUXEL_ROOT}/tools/dedupe-assets.sh" ]; then
        log_info "  ✓ preparing per-app assets via tools/dedupe-assets.sh"
        "${NUXEL_ROOT}/tools/dedupe-assets.sh" || true
    else
        log_warn "  ✗ tools/dedupe-assets.sh not found — per-app assets not prepared"
    fi

    # Wallpaper directory
    mkdir -p "${ROOTFS_DIR}/usr/share/nuxel/wallpapers"
    
    # Install background wallpaper
    if [ -f "${NUXEL_ROOT}/assets/nuxel-background.png" ]; then
        install -Dm644 "${NUXEL_ROOT}/assets/nuxel-background.png"             "${ROOTFS_DIR}/usr/share/nuxel/wallpapers/nuxel-background.png"
        log_info "  ✓ nuxel-background.png"
    elif [ -f "${NUXEL_ROOT}/assets/nuxel-background.png" ]; then
        install -Dm644 "${NUXEL_ROOT}/assets/nuxel-background.png"             "${ROOTFS_DIR}/usr/share/nuxel/wallpapers/nuxel-background.png"
        log_info "  ✓ nuxel-background.png (from canonical assets)"
    else
        log_warn "  ✗ nuxel-background.png not found"
    fi
    
    # Boot animation directory
    mkdir -p "${ROOTFS_DIR}/usr/share/nuxel/boot"
    
    # Install boot animation
    if [ -f "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4" ]; then
        install -Dm644 "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4"             "${ROOTFS_DIR}/usr/share/nuxel/boot/nuxel-boot-animation.mp4"
        log_info "  ✓ nuxel-boot-animation.mp4"
    elif [ -f "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4" ]; then
        install -Dm644 "${NUXEL_ROOT}/assets/nuxel-boot-animation.mp4"             "${ROOTFS_DIR}/usr/share/nuxel/boot/nuxel-boot-animation.mp4"
        log_info "  ✓ nuxel-boot-animation.mp4 (from canonical assets)"
    else
        log_warn "  ✗ nuxel-boot-animation.mp4 not found"
    fi
    
    # Create symlink for Phosh wallpaper
    mkdir -p "${ROOTFS_DIR}/usr/share/backgrounds/nuxel"
    ln -sf /usr/share/nuxel/wallpapers/nuxel-background.png         "${ROOTFS_DIR}/usr/share/backgrounds/nuxel/default.png" 2>/dev/null || true
    
    # Create symlink for Phosh lockscreen wallpaper
    ln -sf /usr/share/nuxel/wallpapers/nuxel-background.png         "${ROOTFS_DIR}/usr/share/backgrounds/nuxel/lockscreen.png" 2>/dev/null || true
    
    # Install Phosh lockscreen CSS theme
    if [ -f "${NUXEL_ROOT}/shell/config/phosh/nuxel-lockscreen.css" ]; then
        mkdir -p "${ROOTFS_DIR}/usr/share/phosh/themes"
        install -Dm644 "${NUXEL_ROOT}/shell/config/phosh/nuxel-lockscreen.css"             "${ROOTFS_DIR}/usr/share/phosh/themes/nuxel-lockscreen.css"
        log_info "  ✓ nuxel-lockscreen.css"
    fi
    
    # Copy wallpaper to PWA app directories for offline access
    for pwa_dir in "${ROOTFS_DIR}/usr/share/nuxel/pwas/nuxel-apps"/*/; do
        [ -d "$pwa_dir" ] && mkdir -p "${pwa_dir}assets" &&             cp "${ROOTFS_DIR}/usr/share/nuxel/wallpapers/nuxel-background.png"                "${pwa_dir}assets/nuxel-background.png" 2>/dev/null || true
    done
    mkdir -p "${ROOTFS_DIR}/usr/share/nuxel/pwas/nuxel-home/assets" &&         cp "${ROOTFS_DIR}/usr/share/nuxel/wallpapers/nuxel-background.png"            "${ROOTFS_DIR}/usr/share/nuxel/pwas/nuxel-home/assets/nuxel-background.png" 2>/dev/null || true
    
    log_ok "Assets installed"

}
# Step 4.6: Install Plymouth animated boot theme
# Converts boot animation MP4 to PNG frame sequence for Plymouth playback
install_plymouth_theme() {
    log_info "[4.6/7] Installing Plymouth boot animation theme..."
    
    local theme_dir="${ROOTFS_DIR}/usr/share/plymouth/themes/nuxel"
    local mp4_path="/usr/share/nuxel/boot/nuxel-boot-animation.mp4"
    
    # Skip if no animation MP4 found
    if [ ! -f "${ROOTFS_DIR}${mp4_path}" ]; then
        log_warn "  Boot animation MP4 not found — skipping Plymouth theme"
        log_warn "  (Place nuxel-boot-animation.mp4 in assets/ to enable)"
        return 0
    fi
    
    # Build the theme via the shared converter (single source of truth; also
    # used by the UTM VM path). It extracts MP4 -> PNG frames and writes the
    # nuxel.plymouth / nuxel.script descriptors into ${theme_dir}.
    local builder="${NUXEL_ROOT}/tools/build-nuxel-boot-theme.sh"
    if [ ! -x "${builder}" ]; then
        log_warn "  tools/build-nuxel-boot-theme.sh not found — skipping Plymouth theme"
        return 0
    fi

    if ! "${builder}" --mp4 "${ROOTFS_DIR}${mp4_path}" --out "${theme_dir}"; then
        log_warn "  Plymouth theme generation failed — theme not installed"
        return 0
    fi

    # Set Plymouth theme globally
    mkdir -p "${ROOTFS_DIR}/etc/plymouth"
    cat > "${ROOTFS_DIR}/etc/plymouth/plymouthd.conf" << CONFEOF
[Daemon]
Theme=nuxel
ShowDelay=0
DeviceTimeout=5
CONFEOF

    log_ok "Plymouth theme installed: ${theme_dir}"
}


# Step 5: Set up directories and permissions
setup_directories() {
    log_info "[5/7] Setting up directories and permissions..."
    
    # Create required directories
    mkdir -p "${ROOTFS_DIR}"/var/{app,lib/{flatpak,nuxel/permissions},log/nuxel,home/user,tmp}
    mkdir -p "${ROOTFS_DIR}"/run/nuxel/bridge
    mkdir -p "${ROOTFS_DIR}"/dev
    mkdir -p "${ROOTFS_DIR}"/proc
    mkdir -p "${ROOTFS_DIR}"/sys
    mkdir -p "${ROOTFS_DIR}"/tmp
    mkdir -p "${ROOTFS_DIR}"/mnt/sdcard
    
    # Create home symlink
    ln -sf /var/home/user "${ROOTFS_DIR}/home"
    
    # Create essential device nodes
    mknod -m 666 "${ROOTFS_DIR}/dev/null" c 1 3 2>/dev/null || true
    mknod -m 666 "${ROOTFS_DIR}/dev/zero" c 1 5 2>/dev/null || true
    mknod -m 666 "${ROOTFS_DIR}/dev/random" c 1 8 2>/dev/null || true
    mknod -m 666 "${ROOTFS_DIR}/dev/urandom" c 1 9 2>/dev/null || true
    
    # Init file enablement (briq-21): create the systemd multi-user.wants
    # dir for the VM target, or enable the OpenRC services at boot for the
    # mustang target. Only the selected init system is set up here.
    if [ x"${NUXEL_INIT}" = xsystemd ]; then
        mkdir -p "${ROOTFS_DIR}/etc/systemd/system/multi-user.target.wants"
    elif [ x"${NUXEL_INIT}" = xopenrc ]; then
        mkdir -p "${ROOTFS_DIR}/etc/init.d"
        for srv in nuxel-bridge nuxel-portal nuxel-notifications nuxel-firstboot; do
            [ -f "${ROOTFS_DIR}/etc/init.d/${srv}" ] || continue
            ln -sf "/etc/init.d/${srv}" "${ROOTFS_DIR}/etc/runlevels/boot/${srv}" 2>/dev/null || true
        done
        log_info "  ✓ OpenRC services linked into boot runlevel (NUXEL_INIT=openrc)"
    fi

    # Install the single-source path config (briq-20) so all services read
    # their runtime/data/config paths from /etc/nuxel/paths.conf with the
    # NUXEL_PATHS_CONF environment override.
    mkdir -p "${ROOTFS_DIR}/etc/nuxel"
    if [ -f "${NUXEL_ROOT}/configs/nuxel/paths.conf" ]; then
        install -Dm644 "${NUXEL_ROOT}/configs/nuxel/paths.conf" \
            "${ROOTFS_DIR}/etc/nuxel/paths.conf"
        log_info "  ✓ /etc/nuxel/paths.conf installed"
    else
        log_warn "  ✗ configs/nuxel/paths.conf not found — paths not installed"
    fi

    # Install the single-source app registry (briq-se1) into the rootfs. The
    # sandbox launcher and nftables.sh both resolve it from
    # /etc/nuxel/app-registry/app_registry.json (read-only system copy); the
    # first-boot stage copies it to /var/lib/nuxel/app-registry/ for runtime.
    if [ -f "${NUXEL_ROOT}/configs/nuxel/app-registry/app_registry.json" ]; then
        install -Dm644 \
            "${NUXEL_ROOT}/configs/nuxel/app-registry/app_registry.json" \
            "${ROOTFS_DIR}/etc/nuxel/app-registry/app_registry.json"
        install -Dm644 \
            "${NUXEL_ROOT}/configs/nuxel/app-registry/app-registry.schema.json" \
            "${ROOTFS_DIR}/etc/nuxel/app-registry/app-registry.schema.json"
        log_info "  ✓ app registry installed to /etc/nuxel/app-registry/"
    else
        log_warn "  ✗ configs/nuxel/app-registry/app_registry.json not found"
    fi

    # Create the first-boot marker so the first-boot wizard runs on the very
    # first boot; the wizard removes it once setup completes (briq-22).
    mkdir -p "${ROOTFS_DIR}/var/lib/nuxel"
    touch "${ROOTFS_DIR}/var/lib/nuxel/.firstboot-complete"
    log_info "  ✓ first-boot marker created at /var/lib/nuxel/.firstboot-complete"

    # Set permissions
    chmod 755 "${ROOTFS_DIR}/var/app"
    chmod 700 "${ROOTFS_DIR}/var/lib/nuxel/permissions"
    chmod 755 "${ROOTFS_DIR}/var/home/user"
    chmod 755 "${ROOTFS_DIR}/run/nuxel"
    chmod 755 "${ROOTFS_DIR}/var/tmp"
    chmod 1777 "${ROOTFS_DIR}/tmp"
    
    # Create system users
    mkdir -p "${ROOTFS_DIR}/etc"
    grep -E "^(root|nuxel-(bridge|portal|notifications)):" /etc/passwd 2>/dev/null \
        >> "${ROOTFS_DIR}/etc/passwd" || true
    grep -E "^(root|nuxel-(bridge|portal|notifications)):" /etc/group 2>/dev/null \
        >> "${ROOTFS_DIR}/etc/group" || true
    
    log_ok "Directories set up"
}

# Step 6: Create the ext4 system image with dm-verity
create_system_image() {
    log_info "[7/7] Creating dm-verity system image..."
    
    # Calculate required size
    local rootfs_size
    rootfs_size=$(du -sm "$ROOTFS_DIR" | awk '{print $1}')
    local image_size=$(( rootfs_size + rootfs_size / 4 + 512 ))
    
    # Use the larger of calculated size or default
    if [ "$image_size" -lt "$SYSTEM_IMG_SIZE_MB" ]; then
        image_size=$SYSTEM_IMG_SIZE_MB
    fi
    
    log_info "Rootfs size: ${rootfs_size} MB, Image size: ${image_size} MB"
    
    # Create sparse image
    rm -f "$SYSTEM_IMG"
    dd if=/dev/zero of="$SYSTEM_IMG" bs=1M count=1 seek=$((image_size - 1)) 2>/dev/null
    
    # Create filesystem
    mkfs.ext4 -O ^has_journal -L "nuxel-system" -F "$SYSTEM_IMG"
    
    # Mount and populate
    local mount_point="${BUILD_OUT}/mnt"
    mkdir -p "$mount_point"
    
    log_info "Populating system image..."
    sudo mount -o loop "$SYSTEM_IMG" "$mount_point"
    sudo rsync -aHAX "$ROOTFS_DIR/" "$mount_point/"
    
    # Flush filesystem
    sudo sync
    
    # Unmount
    sudo umount "$mount_point"
    rmdir "$mount_point" 2>/dev/null || true
    
    # Check filesystem
    e2fsck -fy "$SYSTEM_IMG" 2>/dev/null || true
    
    # Resize to minimum
    resize2fs -M "$SYSTEM_IMG" 2>/dev/null
    
    # Create dm-verity hash tree
    log_info "Creating dm-verity hash tree..."
    local root_hash
    root_hash=$(veritysetup format \
        --hash=sha256 \
        --salt="$(openssl rand -hex 32)" \
        "$SYSTEM_IMG" \
        "${SYSTEM_IMG}.verity" 2>&1 | grep 'Root hash:' | awk '{print $3}')
    
    echo "$root_hash" > "${BUILD_OUT}/system.root_hash"
    
    log_ok "System image: ${SYSTEM_IMG} ($(du -h $SYSTEM_IMG | awk '{print $1}'))"
    log_ok "Verity data: ${SYSTEM_IMG}.verity"
    log_ok "Root hash: ${root_hash}"
    
    # Copy verity data alongside the image
    cp "$SYSTEM_IMG" "${BUILD_OUT}/system.img.raw"
    cp "${SYSTEM_IMG}.verity" "${BUILD_OUT}/"
}

# Print summary
print_summary() {
    echo ""
    log_info "======================================"
    log_info "  Rootfs Build Complete"
    log_info "======================================"
    echo ""
    log_info "Rootfs size: $(du -sh "$ROOTFS_DIR" | awk '{print $1}')"
    if [ -f "$SYSTEM_IMG" ]; then
        log_info "System image: $(du -h "$SYSTEM_IMG" | awk '{print $1}')"
    else
        log_info "System image: not built (NUXEL_MKROOTFS_IMAGE=0)"
    fi
    if [ -f "${SYSTEM_IMG}.verity" ]; then
        log_info "Verity data: $(du -h "${SYSTEM_IMG}.verity" | awk '{print $1}')"
    fi
    echo ""
    log_info "Contents:"
    log_info "  Services: nuxel-bridge, nuxel-portal, nuxel-notifications"
    log_info "  Native apps: dialer, messages, contacts, settings"
    log_info "  Security: hardened_malloc, AppArmor, nftables, sysctl"
    echo ""
    log_info "Next steps:"
    log_info "  1. ./tools/sign-image.sh all  (sign images)"
    log_info "  2. ./vm/nuxel-vm-bootstrap.sh    (VM boot test)"
    echo ""
}

# =============================================================================
# Portable `install -D` shim
# -----------------------------------------------------------------------------
# Every install below uses GNU coreutils' `install -Dm<mode> <src> <dst>`
# (create parent dirs + set mode). BSD/macOS install(1) has no -D, which meant
# the staging tree could only be produced on a GNU host. Provide a compatible
# shim so the same builder works on macOS dev boxes and Linux CI.
# =============================================================================
if ! install --version 2>/dev/null | grep -q 'GNU coreutils'; then
    install() {
        local mode="" make_dirs=0
        while [ $# -gt 0 ]; do
            case "$1" in
                -D)      make_dirs=1; shift ;;
                -Dm*)    make_dirs=1; mode="${1#-Dm}"; shift ;;
                -m)      mode="$2"; shift 2 ;;
                -o|-g)   shift 2 ;;
                -p|-c|-b|-S|-f|-v) shift ;;
                -*)      shift ;;
                *)       break ;;
            esac
        done
        [ $# -ge 2 ] || { echo "install(shim): expected <src> <dst>" >&2; return 1; }
        local dest src n=$#
        # GNU semantics: last argument is the destination.
        eval "dest=\${$n}"
        local i s
        for (( i=1; i<n; i++ )); do
            eval "src=\${$i}"
            if [ -d "$src" ]; then
                mkdir -p "$dest"
                cp -R "$src/." "$dest/" 2>/dev/null || return 1
            else
                mkdir -p "$(dirname "$dest")"
                cp "$src" "$dest" || return 1
                [ -n "$mode" ] && chmod "$mode" "$dest"
            fi
        done
        return 0
    }
fi

# =============================================================================
# Main — build the device-agnostic Nuxel userspace staging tree.
# -----------------------------------------------------------------------------
# Output: ${ROOTFS_DIR} (build/out/rootfs), the staging tree the per-device
# image builders bake into an ext4 rootfs.
#
# The dm-verity `system.img` step (create_system_image) needs root privileges
# (loop mount) + veritysetup, so it is opt-in via NUXEL_MKROOTFS_IMAGE=1; the
# Phase-1 phone images bake their own writable ext4 from this staging tree.
#
# Steps are individually non-fatal: a missing optional tool (flatpak, GTK4,
# plymouth, ...) degrades the tree, it does not abort the build. Genuine
# incompleteness is caught by tools/verify-artifacts.sh, which is fail-closed.
# =============================================================================
main() {
    run_step() {
        local name="$1"; shift
        if "$@"; then
            return 0
        fi
        log_warn "step '${name}' failed — continuing (verify-artifacts.sh is the gate)"
        return 0
    }

    run_step "clean"                 clean
    run_step "flatpak-base"          install_flatpak_base
    run_step "core-services"         install_core_services
    run_step "native-apps"           install_native_apps
    run_step "security-configs"      install_security_configs
    run_step "assets"                install_assets
    run_step "plymouth-theme"        install_plymouth_theme
    run_step "directories"           setup_directories

    if [ "${NUXEL_MKROOTFS_IMAGE:-0}" = "1" ]; then
        run_step "dm-verity-image"   create_system_image
    else
        log_info "[6/7] Skipping dm-verity system.img (Phase-1 images bake their own ext4;"
        log_info "      set NUXEL_MKROOTFS_IMAGE=1 to also emit build/out/system.img)"
    fi

    print_summary
    return 0
}

main "$@"
