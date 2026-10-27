#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/power-menu.js
# previous-hash: f51580c53fba527538340b6843b89b878618d0ea120755ea4325bb531cfe8936
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged
printf '%s  %s\n' f51580c53fba527538340b6843b89b878618d0ea120755ea4325bb531cfe8936 /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js | grep -q f51580c53fba527538340b6843b89b878618d0ea120755ea4325bb531cfe8936
echo INSTALL-OK
