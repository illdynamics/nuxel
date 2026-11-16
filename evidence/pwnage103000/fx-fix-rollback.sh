#!/bin/sh
# PWNAGE-103000 Edge FX follow-up rollback (userspace only; no partition change).
# Restores the files captured immediately before the Preview/Allow-all fix.
set -eu
B=/root/nuxel-backup-103000-fxfix-20261112T103651Z
[ -d "$B" ] || { echo "backup missing: $B" >&2; exit 1; }
D=/usr/share/nuxel/pwa
install -m 644 -o root -g root "$B/home-js/edge-lighting.js" "$D/nuxel-home/js/edge-lighting.js"
install -m 644 -o root -g root "$B/home-css/edge-lighting.css" "$D/nuxel-home/css/edge-lighting.css"
for f in edge-fx.js index.html edge-fx.css; do
  install -m 644 -o root -g root "$B/edge-fx/$f" "$D/nuxel-apps/edge-fx/$f"
done
install -m 644 -o root -g root "$B/bridge/edge_lighting_provider.py" /usr/lib/nuxel/nuxel-bridge/edge_lighting_provider.py
install -m 644 -o root -g root "$B/edge-default/edge-lighting.json" /etc/nuxel/edge-lighting/edge-lighting.json
# The service-worker version files were not present in the pre-fix backup as a
# group; restore the known pre-fix v096 marker only if the operator asks for a
# full rollback of the cache bump.
if [ "${RESTORE_V096:-0}" = "1" ]; then
  sed -i "s/const CACHE_VERSION = 'v097-p103000';/const CACHE_VERSION = 'v096-p103000';/" "$D/nuxel-home/sw.js"
  sed -i 's/"cache_version": "v097-p103000"/"cache_version": "v096-p103000"/' "$D/nuxel-home/manifest.json"
fi
systemctl restart nuxel-http-bridge
sleep 2
systemctl is-active nuxel-http-bridge
echo "fx-fix rollback done (settings under /var/lib/nuxel/edge-lighting preserved)."
