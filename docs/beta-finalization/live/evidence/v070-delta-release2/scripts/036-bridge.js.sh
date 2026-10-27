#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-common/bridge.js (service: None, risk: low)
# staged source: pwa/nuxel-common/bridge.js
# previous-hash: d0b9645e26dd2c043c345e7c24de6bb433e1475e347a1782f3b9c24d284a3e54
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-v070-delta-release2 /usr/share/nuxel/pwa/nuxel-common/bridge.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-v070-delta-release2; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged
printf '%s  %s\n' d0b9645e26dd2c043c345e7c24de6bb433e1475e347a1782f3b9c24d284a3e54 /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | grep -q d0b9645e26dd2c043c345e7c24de6bb433e1475e347a1782f3b9c24d284a3e54
echo INSTALL-OK
