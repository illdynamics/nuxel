#!/bin/sh
# PWNAGE-85000 rollback helper. Review before running as root.
set -eu
B=/var/backups/nuxel/p85000-20261106T163134Z
install -m644 "$B/bridge/flatpak_provider.py" /usr/lib/nuxel/nuxel-bridge/flatpak_provider.py
install -m644 "$B/bridge/api.py" /usr/lib/nuxel/nuxel-bridge/api.py
install -m644 "$B/bridge/hw_providers.py" /usr/lib/nuxel/nuxel-bridge/hw_providers.py
install -m644 "$B/pwa/common/theme.css" /usr/share/nuxel/pwa/nuxel-common/theme.css
install -m644 "$B/pwa/common/theme.js" /usr/share/nuxel/pwa/nuxel-common/theme.js
install -m644 "$B/pwa/home/css/style.css" /usr/share/nuxel/pwa/nuxel-home/css/style.css
install -m644 "$B/pwa/home/css/launcher.css" /usr/share/nuxel/pwa/nuxel-home/css/launcher.css
install -m644 "$B/pwa/home/js/app.js" /usr/share/nuxel/pwa/nuxel-home/js/app.js
install -m644 "$B/pwa/home/js/launcher.js" /usr/share/nuxel/pwa/nuxel-home/js/launcher.js
install -m644 "$B/pwa/home/index.html" /usr/share/nuxel/pwa/nuxel-home/index.html
install -m644 "$B/pwa/home/sw.js" /usr/share/nuxel/pwa/nuxel-home/sw.js
install -m644 "$B/pwa/settings/index.html" /usr/share/nuxel/pwa/nuxel-apps/settings/index.html
install -m644 "$B/pwa/settings/appearance-settings.js" /usr/share/nuxel/pwa/nuxel-apps/settings/appearance-settings.js
systemctl disable --now nuxel-fuse-access.service || true
rm -f /etc/systemd/system/nuxel-fuse-access.service
install -m644 "$B/etc/nuxel-portal-doc.conf" /etc/tmpfiles.d/nuxel-portal-doc.conf
systemctl daemon-reload
systemctl restart nuxel-http-bridge nuxel-bridge
