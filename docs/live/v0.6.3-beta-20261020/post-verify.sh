#!/bin/sh
set -u
echo "=== POST-DEPLOY WEB HASHES ==="
cd /usr/share/nuxel || exit 1
for f in pwa/nuxel-home/index.html pwa/nuxel-home/manifest.json pwa/nuxel-home/sw.js pwa/nuxel-home/css/style.css pwa/nuxel-home/css/launcher.css pwa/nuxel-home/js/launcher.js pwa/nuxel-home/js/gestures.js pwa/nuxel-home/js/home-settings.js pwa/nuxel-home/js/apps.js pwa/nuxel-home/assets/nuxel-bottom-bar.jpg pwa/nuxel-home/assets/nuxel-bottom-bar2.png assets/nuxel-bottom-bar.jpg assets/nuxel-bottom-bar2.png pwa/nuxel-apps/settings/index.html pwa/nuxel-apps/settings/settings.css pwa/nuxel-apps/settings/wifi-settings.js pwa/nuxel-common/app-registry.json; do
    sha256sum "$f"
done
echo "=== POST-DEPLOY BRIDGE HASHES ==="
sha256sum /usr/bin/nuxel-bridge /usr/bin/nuxel-http-bridge /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/api.py
echo "=== SERVICES ==="
systemctl is-active nuxel-web nuxel-bridge nuxel-http-bridge nuxel-wayland NetworkManager
systemctl show -p MainPID -p ActiveState -p SubState nuxel-bridge nuxel-http-bridge | sed 's/^/  /'
echo "=== HTTP ==="
for r in /pwa/nuxel-home/index.html /pwa/nuxel-home/css/launcher.css /pwa/nuxel-home/assets/nuxel-bottom-bar.jpg /pwa/nuxel-home/assets/nuxel-bottom-bar2.png /pwa/nuxel-apps/settings/index.html /pwa/nuxel-apps/settings/wifi-settings.js /pwa/nuxel-apps/browser/index.html /pwa/nuxel-common/app-registry.json; do
    printf '%s ' "$r"
    curl -s -o /dev/null -w '%{http_code} %{size_download}\n' --max-time 3 "http://127.0.0.1:8000$r"
done
echo "=== BRIDGE API ==="
curl -s --max-time 3 http://127.0.0.1:8080/api/v1/ping
echo
curl -s --max-time 3 http://127.0.0.1:8080/api/v1/health
echo
echo "=== PIDS ==="
pgrep -af 'nuxel-pwa-host|http.server 8000|WebKitWebProcess|nuxel-bridge' || true
