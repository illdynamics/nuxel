#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/wifi-settings.js
# previous-hash: c636ce914fb4ea54fc23a8887a9a15e487030d76a9c0ceed4d838fbaa0d9af77
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-staged
printf '%s  %s\n' c636ce914fb4ea54fc23a8887a9a15e487030d76a9c0ceed4d838fbaa0d9af77 /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/wifi-settings.js | grep -q c636ce914fb4ea54fc23a8887a9a15e487030d76a9c0ceed4d838fbaa0d9af77
echo INSTALL-OK
