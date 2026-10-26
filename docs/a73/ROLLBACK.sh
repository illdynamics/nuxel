#!/bin/sh
# NUXEL A73/22000 — reviewed rollback. NEVER reboots/flashes without approval.
set -eu
BK=/var/lib/nuxel/a73-backup
B=/usr/lib/nuxel/nuxel-bridge
P=/usr/share/nuxel/pwa/nuxel-home

echo "== Restore bridge (Python) =="
cp -a "$BK/bridge/system_indicators.py.a73-pre" "$B/system_indicators.py"
cp -a "$BK/bridge/api.py" "$B/api.py"
cp -a "$BK/bridge/bridge.py" "$B/bridge.py"
cp -a "$BK/bridge/capabilities.py" "$B/capabilities.py"

echo "== Restore launcher PWA =="
cp -a "$BK/pwa-home/js/qs.js" "$P/js/qs.js"

echo "== Restore native host =="
cp -a "$BK/nuxel-pwa-host" /usr/lib/nuxel/nuxel-pwa-host

echo "== Restart services + launcher =="
systemctl restart nuxel-bridge.service nuxel-http-bridge.service
systemctl restart nuxel-wayland.service

echo "== Stop the A73 evidence logger =="
pkill -f '/usr/lib/nuxel/a73-logger.sh' || true

echo "ROLLBACK COMPLETE"
