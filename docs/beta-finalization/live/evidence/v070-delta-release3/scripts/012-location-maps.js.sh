#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/location-maps.js
# previous-hash: b0cfeefe39aaf11355e9220ab864a1155eda30ffba9cb4e718e848e652411a6e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-rollback.pre-v070-delta-release3 /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-staged
printf '%s  %s\n' b0cfeefe39aaf11355e9220ab864a1155eda30ffba9cb4e718e848e652411a6e /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/location-maps.js | grep -q b0cfeefe39aaf11355e9220ab864a1155eda30ffba9cb4e718e848e652411a6e
echo INSTALL-OK
