#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/js/files.js
# previous-hash: 643dbf4f6f98930251b5d574959fa04b01c97b80616cbe971004bc4c6d04d282
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-staged
printf '%s  %s\n' 643dbf4f6f98930251b5d574959fa04b01c97b80616cbe971004bc4c6d04d282 /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js | grep -q 643dbf4f6f98930251b5d574959fa04b01c97b80616cbe971004bc4c6d04d282
echo INSTALL-OK
