#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/settings-model.js
# previous-hash: 5151b39723276ff627709ef819da3fd7d6d31bff3de020b0093c4bb9d95d63b7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-staged
printf '%s  %s\n' 5151b39723276ff627709ef819da3fd7d6d31bff3de020b0093c4bb9d95d63b7 /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js | grep -q 5151b39723276ff627709ef819da3fd7d6d31bff3de020b0093c4bb9d95d63b7
echo INSTALL-OK
