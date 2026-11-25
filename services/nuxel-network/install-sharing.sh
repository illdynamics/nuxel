#!/bin/bash
# Reversible deployment of native LTE sharing; never edits the USB gadget.
set -euo pipefail
[[ $(id -u) = 0 ]] || { echo 'requires root' >&2; exit 1; }
repo=$(cd "$(dirname "$0")/../.." && pwd)
for command in hostapd dnsmasq nft iptables nmcli; do command -v "$command" >/dev/null; done
[[ -f /etc/systemd/system/nuxel-cellular-lock.service ]]
backup=$(mktemp -d /var/lib/nuxel/sharing-install.XXXXXX)
paths=(/usr/libexec/nuxel/nuxel-hotspot /usr/libexec/nuxel/nuxel-usb-tether
       /etc/systemd/system/nuxel-hotspot.service /etc/systemd/system/nuxel-usb-tether.service
       /etc/systemd/system/nuxel-http-bridge.service.d/40-network-status.conf)
for name in native_radio mobile_upstream sharing_link usb_tether network_manager api; do
    paths+=("/usr/lib/nuxel/nuxel-bridge/$name.py")
done
ui_files=(nuxel-apps/settings/index.html nuxel-apps/settings/driver-diagnostics.js
          nuxel-apps/settings/usb-network-settings.js nuxel-home/js/qs.js
          nuxel-home/index.html nuxel-home/js/status-bar.js nuxel-home/css/status-bar.css)
for name in "${ui_files[@]}"; do paths+=("/usr/share/nuxel/pwa/$name"); done
printf '%s\n' "${paths[@]}" > "$backup/paths"
for path in "${paths[@]}"; do
    if [[ -e "$path" ]]; then mkdir -p "$backup$(dirname "$path")"; cp -a "$path" "$backup$path"; fi
done
cat > "$backup/rollback.sh" <<'ROLLBACK'
#!/bin/bash
set -euo pipefail
base=$(cd "$(dirname "$0")" && pwd)
systemctl stop nuxel-hotspot nuxel-usb-tether
while IFS= read -r path; do
    rm -f "$path"
    if [[ -e "$base$path" ]]; then cp -a "$base$path" "$path"; fi
done < "$base/paths"
systemctl daemon-reload
systemctl restart nuxel-http-bridge
ROLLBACK
chmod 0700 "$backup/rollback.sh"
trap '"$backup/rollback.sh"' ERR
systemctl stop nuxel-hotspot nuxel-usb-tether
install -m 0755 "$repo/services/nuxel-network/nuxel-hotspot.py" /usr/libexec/nuxel/nuxel-hotspot
install -m 0755 "$repo/services/nuxel-remote-access/bin/nuxel-usb-tether" /usr/libexec/nuxel/nuxel-usb-tether
install -m 0644 "$repo/services/nuxel-network/nuxel-hotspot.service" /etc/systemd/system/
install -m 0644 "$repo/services/nuxel-remote-access/systemd/nuxel-usb-tether.service" /etc/systemd/system/
mkdir -p /etc/systemd/system/nuxel-http-bridge.service.d
cat > /etc/systemd/system/nuxel-http-bridge.service.d/40-network-status.conf <<'CONF'
[Service]
# Extend the existing allowlist for native route/interface status queries.
RestrictAddressFamilies=AF_NETLINK
CONF
for name in native_radio mobile_upstream sharing_link usb_tether network_manager api; do
    install -m 0644 "$repo/services/nuxel-bridge/src/$name.py" "/usr/lib/nuxel/nuxel-bridge/$name.py"
done
for name in "${ui_files[@]}"; do
    install -m 0644 "$repo/pwa/$name" "/usr/share/nuxel/pwa/$name"
done
# Sharing activation is explicit for every boot.
systemctl disable nuxel-hotspot nuxel-usb-tether
systemctl daemon-reload
trap - ERR
echo "Installed. Rollback: $backup/rollback.sh"
echo 'Restart nuxel-http-bridge explicitly to load the providers.'
