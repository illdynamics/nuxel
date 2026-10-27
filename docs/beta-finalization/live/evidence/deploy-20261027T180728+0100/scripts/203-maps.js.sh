#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/maps/js/maps.js
# previous-hash: f0e303322f6eb3e48145fd553392d548e81867d6ecf0866c8b45c1083b316964
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-staged
printf '%s  %s\n' f0e303322f6eb3e48145fd553392d548e81867d6ecf0866c8b45c1083b316964 /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js | grep -q f0e303322f6eb3e48145fd553392d548e81867d6ecf0866c8b45c1083b316964
echo INSTALL-OK
