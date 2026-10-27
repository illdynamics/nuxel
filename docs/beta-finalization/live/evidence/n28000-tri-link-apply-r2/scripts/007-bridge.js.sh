#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-common/bridge.js (service: None, risk: low)
# staged source: pwa/nuxel-common/bridge.js
# previous-hash: 052277e2e6f217bcfb88d70b5d4d9f4cb738eb5adeaf597f9fc0b0f2960a2581
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-n28000-tri-link-apply-r2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-n28000-tri-link-apply-r2 /usr/share/nuxel/pwa/nuxel-common/bridge.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-n28000-tri-link-apply-r2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-n28000-tri-link-apply-r2; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged
printf '%s  %s\n' 052277e2e6f217bcfb88d70b5d4d9f4cb738eb5adeaf597f9fc0b0f2960a2581 /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | grep -q 052277e2e6f217bcfb88d70b5d4d9f4cb738eb5adeaf597f9fc0b0f2960a2581
echo INSTALL-OK
