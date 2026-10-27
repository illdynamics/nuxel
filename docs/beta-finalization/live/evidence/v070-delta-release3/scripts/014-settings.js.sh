#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/settings.js
# previous-hash: 93cedc2b5a9faf53ed777b9473adc58e3395415e48dc34ac0abd5967c2076a4d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback.pre-v070-delta-release3 /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-staged
printf '%s  %s\n' 93cedc2b5a9faf53ed777b9473adc58e3395415e48dc34ac0abd5967c2076a4d /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js | grep -q 93cedc2b5a9faf53ed777b9473adc58e3395415e48dc34ac0abd5967c2076a4d
echo INSTALL-OK
