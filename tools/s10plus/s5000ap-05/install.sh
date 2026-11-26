#!/usr/bin/env bash
# install.sh — REVERSIBLE deployment of nuxel-radiod onto a normally-booted Nuxel.
# SPDX-License-Identifier: GPL-2.0-only
# Builds for the native architecture, installs binary + unit, enables the
# OBSERVER-ONLY service. It does NOT enable or trigger any CP boot.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_BIN=/usr/libexec/nuxel
DEST_SYS=/etc/systemd/system

if [[ "${1:-}" == "--uninstall" ]]; then
    systemctl disable --now nuxel-radiod.service 2>/dev/null || true
    rm -f "$DEST_SYS/nuxel-radiod.service" "$DEST_BIN/nuxel-radiod" "$DEST_BIN/nuxel-cellular-link" "$DEST_BIN/cellular_link.py" "$DEST_BIN/cellular_nm.py" \
        /etc/dbus-1/system.d/nl.nuxel.Radio1.conf /etc/NetworkManager/dispatcher.d/device/nuxel-cellular
    systemctl daemon-reload
    echo "uninstalled nuxel-radiod"
    exit 0
fi

[[ $(id -u) -eq 0 ]] || { echo "run as root"; exit 1; }
mkdir -p "$DEST_BIN" "$DEST_SYS" /var/lib/nuxel

CFLAGS=(-O2 -Wall -Wextra -Werror -std=gnu11)
echo "building nuxel-radiod for $(uname -m)..."
gcc "${CFLAGS[@]}" -I"$HERE/src" -o "$HERE/nuxel-radiod" \
    "$HERE/src/radiod.c" "$HERE/src/oes_cert.c" "$HERE/src/transport.c" "$HERE/src/sipc5_fmt.c" \
    "$HERE/src/rfs_proto.c" "$HERE/src/rfs_respond.c" "$HERE/src/fmt_tx.c" \
    "$HERE/src/fmt_rx.c" "$HERE/src/data_session.c" "$HERE/src/mbim_tx.c" "$HERE/src/rfs_nv.c" "$HERE/src/efs_nv.c" "$HERE/src/nv_items.c" \
    "$HERE/src/fmt_sms.c" "$HERE/src/sms_pdu.c" "$HERE/src/sms_store.c" "$HERE/src/sms_service.c" \
    "$HERE/src/fmt_call.c" "$HERE/src/call_service.c" "$HERE/src/cellular_link.c" "$HERE/src/mobile_data.c" \
    "$HERE/src/ims_pdn.c" "$HERE/src/ims_service.c" "$HERE/src/ims_init.c" \
    "$HERE/src/ims_iil.c" "$HERE/src/ims_iil_rx.c" "$HERE/src/iil_pdn.c" "$HERE/src/iil_auth.c" \
    "$HERE/src/ims_sdm.c" \
    "$HERE/src/ims_sip.c" "$HERE/src/ims_sip_tr.c" "$HERE/src/ims_security.c" "$HERE/src/ims_sms.c" -lsystemd -lsqlite3
# Preserve the complete replaced userspace files before the first installation.
backup=$(mktemp -d /var/lib/nuxel/radio-install.XXXXXX)
paths=("$DEST_BIN/nuxel-radiod" "$DEST_BIN/nuxel-cellular-link"
       "$DEST_BIN/cellular_link.py" "$DEST_BIN/cellular_nm.py"
       "$DEST_SYS/nuxel-radiod.service" /etc/dbus-1/system.d/nl.nuxel.Radio1.conf
       /etc/NetworkManager/dispatcher.d/device/nuxel-cellular)
if [[ "${1:-}" == "--with-ui" ]]; then
    repo=$(cd "$HERE/../../.." && pwd)
    native="$repo/tools/s10plus/a45"
    wayland-scanner client-header "$native/wlr-layer-shell-unstable-v1.xml" "$HERE/wlr-layer-shell-unstable-v1-client-protocol.h"
    wayland-scanner private-code "$native/wlr-layer-shell-unstable-v1.xml" "$HERE/wlr-layer-shell-unstable-v1-protocol.c"
    wayland-scanner private-code "$native/xdg-shell.xml" "$HERE/xdg-shell-protocol.c"
    gcc -O2 -Wall -I"$HERE" $(pkg-config --cflags wayland-client cairo pangocairo) \
        -o "$HERE/nuxel-statusbar" "$native/nuxel-statusbar.c" "$HERE/wlr-layer-shell-unstable-v1-protocol.c" "$HERE/xdg-shell-protocol.c" \
        $(pkg-config --libs wayland-client cairo pangocairo)
    paths+=(/usr/lib/nuxel/nuxel-statusbar /usr/share/nuxel/permissions/nuxel-settings.json
            /var/lib/nuxel/permissions/nuxel-settings.json)
    for f in native_radio.py bridge.py api.py; do
        paths+=("/usr/lib/nuxel/nuxel-bridge/$f")
        test -f "$repo/services/nuxel-bridge/src/$f"
    done
    for f in nuxel-home/js/qs.js nuxel-home/js/status-bar.js nuxel-apps/settings/index.html nuxel-apps/settings/driver-diagnostics.js nuxel-apps/settings/manifest.json; do
        paths+=("/usr/share/nuxel/pwa/$f")
        test -f "$repo/pwa/$f"
    done
fi
printf '%s\n' "${paths[@]}" > "$backup/paths.list"
for file in "${paths[@]}"; do
    if [[ -e "$file" ]]; then
        mkdir -p "$backup$(dirname "$file")"
        cp -a "$file" "$backup$file"
    else
        printf '%s\n' "$file" >> "$backup/absent"
    fi
done
cat > "$backup/rollback.sh" <<'ROLLBACK'
#!/bin/bash
set -euo pipefail
backup=$(cd "$(dirname "$0")" && pwd)
while IFS= read -r path; do
    if [[ -e "$backup$path" || -L "$backup$path" ]]; then
        cp -a -- "$backup$path" "$path.rollback-new"
        mv -f -- "$path.rollback-new" "$path"
    else
        rm -f -- "$path"
    fi
done < "$backup/paths.list"
systemctl daemon-reload
ROLLBACK
chmod 0700 "$backup/rollback.sh"
trap '"$backup/rollback.sh"' ERR
install -m 0755 "$HERE/nuxel-radiod" "$DEST_BIN/nuxel-radiod"
install -m 0755 "$HERE/scripts/cellular_link.py" "$DEST_BIN/nuxel-cellular-link"
install -m 0644 "$HERE/scripts/cellular_link.py" "$DEST_BIN/cellular_link.py"
install -m 0644 "$HERE/scripts/cellular_nm.py" "$DEST_BIN/cellular_nm.py"
install -D -m 0755 "$HERE/scripts/nuxel-cellular" /etc/NetworkManager/dispatcher.d/device/nuxel-cellular
install -D -m 0644 "$HERE/nl.nuxel.Radio1.conf" /etc/dbus-1/system.d/nl.nuxel.Radio1.conf
install -m 0644 "$HERE/nuxel-radiod.service" "$DEST_SYS/nuxel-radiod.service"
if [[ "${1:-}" == "--with-ui" ]]; then
    install -m 0755 "$HERE/nuxel-statusbar" /usr/lib/nuxel/nuxel-statusbar
    install -m 0644 "$repo/configs/nuxel/permissions/nuxel-settings.json" /usr/share/nuxel/permissions/nuxel-settings.json
    python3 "$HERE/scripts/migrate_settings_network_grant.py"
    for f in native_radio.py bridge.py api.py; do
        install -m 0644 "$repo/services/nuxel-bridge/src/$f" "/usr/lib/nuxel/nuxel-bridge/$f"
    done
    for f in nuxel-home/js/qs.js nuxel-home/js/status-bar.js nuxel-apps/settings/index.html nuxel-apps/settings/driver-diagnostics.js nuxel-apps/settings/manifest.json; do
        install -m 0644 "$repo/pwa/$f" "/usr/share/nuxel/pwa/$f"
    done
fi
systemctl daemon-reload
systemctl enable nuxel-radiod.service
trap - ERR
echo "Rollback: $backup/rollback.sh (then restart affected services)"
echo "Installed; services not restarted. Existing production boot and data-path drop-ins retained."
