#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/layout-model.js
# previous-hash: d2bd5fb9a5bdab00572730e4d4ba472e22413f771557c79ed246920d064b7936
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-staged
printf '%s  %s\n' d2bd5fb9a5bdab00572730e4d4ba472e22413f771557c79ed246920d064b7936 /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/layout-model.js | grep -q d2bd5fb9a5bdab00572730e4d4ba472e22413f771557c79ed246920d064b7936
echo INSTALL-OK
