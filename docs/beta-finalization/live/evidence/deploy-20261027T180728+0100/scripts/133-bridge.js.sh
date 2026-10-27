#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/bridge.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/bridge.js
# previous-hash: b84f2789fb3687b514b1fb7d6915e100b8887b877b0aff4d870228e622122585
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/bridge.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bridge.js /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bridge.js /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged
printf '%s  %s\n' b84f2789fb3687b514b1fb7d6915e100b8887b877b0aff4d870228e622122585 /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bridge.js | grep -q b84f2789fb3687b514b1fb7d6915e100b8887b877b0aff4d870228e622122585
echo INSTALL-OK
