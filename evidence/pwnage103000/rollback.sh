#!/bin/sh
# PWNAGE-103000 rollback (userspace only; no partition is touched).
#
# Restores the pre-mission userspace artifacts captured at 20261112T093450Z and undoes the
# app-registry entry.  Usage:  ssh root@192.168.178.167 'sh -s' < rollback.sh
set -eu
B=/root/nuxel-backup-103000-20261112T093450Z
[ -d "$B" ] || { echo "backup missing: $B" >&2; exit 1; }

# 1) Bridge provider + torches back to their pre-mission files.
cd /usr/lib/nuxel/nuxel-bridge
tar -xzf "$B/nuxel-bridge-pre-103000.tgz"
# The new provider module must not be left active next to the old api.py.
rm -f /usr/lib/nuxel/nuxel-bridge/edge_lighting_provider.py

# 2) Launcher tree, shared client, Settings, registry (pre-mission copies).
cd /usr/share/nuxel
tar -xzf "$B/pwa-pre-103000/home-pre.tgz"
tar -xzf "$B/pwa-pre-103000/common-settings-pre.tgz"

# 3) Edge FX app bundle and default policy are additive; remove only what this
#    mission created.  Settings + user data are preserved.
rm -rf /usr/share/nuxel/pwa/nuxel-apps/edge-fx
rm -f /usr/share/nuxel/pwa/nuxel-apps/settings/edge-lighting-settings.js
rm -f /etc/nuxel/edge-lighting/edge-lighting.json
rmdir /etc/nuxel/edge-lighting 2>/dev/null || true
# Keep /var/lib/nuxel/edge-lighting (user settings + event journal) unless the
# owner explicitly asks to purge it; the rolled-back engine ignores it.

# 4) Restart only the HTTP bridge (it re-imports api.py / providers).
systemctl restart nuxel-http-bridge
sleep 2
systemctl is-active nuxel-http-bridge
echo "rollback done. Re-open Home (Settings -> Apps -> Edge FX, or reload the"
echo "launcher) so WebKit drops the cached v096 service-worker bundle."
