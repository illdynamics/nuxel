#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/hardware-settings.js
# previous-hash: 66c7fb23a6a6b3c77b9dff75840fb1003b992a282054be147d900bb836096884
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T181844-2200732 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T181844-2200732 /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T181844-2200732 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T181844-2200732; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged
printf '%s  %s\n' 66c7fb23a6a6b3c77b9dff75840fb1003b992a282054be147d900bb836096884 /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js | grep -q 66c7fb23a6a6b3c77b9dff75840fb1003b992a282054be147d900bb836096884
echo INSTALL-OK
