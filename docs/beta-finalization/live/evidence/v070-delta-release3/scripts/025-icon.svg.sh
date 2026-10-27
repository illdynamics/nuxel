#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console-wifi/icons/icon.svg
# previous-hash: 57da8f57c7ebe18a69e6bd4a2e5f1cd1aa239ef3bf881f3ddf1431a3ab0a1529
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-rollback.pre-v070-delta-release3 /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-staged
printf '%s  %s\n' 57da8f57c7ebe18a69e6bd4a2e5f1cd1aa239ef3bf881f3ddf1431a3ab0a1529 /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-wifi/icons/icon.svg | grep -q 57da8f57c7ebe18a69e6bd4a2e5f1cd1aa239ef3bf881f3ddf1431a3ab0a1529
echo INSTALL-OK
