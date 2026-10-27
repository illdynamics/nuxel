#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console/console.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console/console.js
# previous-hash: bd20a9c139d03800ef3f9d1e1fc43d8805c8739e34cf2ed77e805304f2c72b11
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-rollback.pre-deploy-20261027T181522-2198480 /usr/share/nuxel/pwa/nuxel-apps/console/console.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/console.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/console.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/console.js /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/console.js /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-rollback.pre-deploy-20261027T181522-2198480; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-staged
printf '%s  %s\n' bd20a9c139d03800ef3f9d1e1fc43d8805c8739e34cf2ed77e805304f2c72b11 /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/console.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/console.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/console.js | grep -q bd20a9c139d03800ef3f9d1e1fc43d8805c8739e34cf2ed77e805304f2c72b11
echo INSTALL-OK
