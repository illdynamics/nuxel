#!/bin/sh
# NUXEL A74 / 23000 — rollback of the USB-unplug fix.
# Restores ONLY the three live files changed this session, then restarts the
# two consumers.  Run as root on the phone (USB console or SSH over Wi-Fi).
set -u
B=/var/lib/nuxel/a74-backup
if [ ! -f "$B/bridge/system_indicators.py.pre-a74" ]; then
  echo "a74-backup missing — refusing to roll back blindly" >&2
  exit 2
fi
cp -a "$B/bridge/system_indicators.py.pre-a74" /usr/lib/nuxel/nuxel-bridge/system_indicators.py
cp -a "$B/bin/nuxel-pwa-host.pre-a74"        /usr/lib/nuxel/nuxel-pwa-host
chmod 0755 /usr/lib/nuxel/nuxel-pwa-host
systemctl restart nuxel-http-bridge.service nuxel-wayland.service
systemctl is-active nuxel-http-bridge.service nuxel-wayland.service
echo "ROLLBACK-DONE; verify hashes:"
sha256sum /usr/lib/nuxel/nuxel-bridge/system_indicators.py /usr/lib/nuxel/nuxel-pwa-host
# expected: 93b2d3d0…bcf67c  (system_indicators.py)
#           cff15529…36d33e3  (nuxel-pwa-host)
