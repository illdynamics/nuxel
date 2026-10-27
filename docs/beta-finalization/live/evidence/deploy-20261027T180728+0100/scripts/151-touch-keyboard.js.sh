#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/touch-keyboard.js
# previous-hash: aac1d0f22c402b49b4cc577a71cf48fd63a09dc2a4e7e74f0645ee2ab8ac7dd6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged
printf '%s  %s\n' aac1d0f22c402b49b4cc577a71cf48fd63a09dc2a4e7e74f0645ee2ab8ac7dd6 /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js | grep -q aac1d0f22c402b49b4cc577a71cf48fd63a09dc2a4e7e74f0645ee2ab8ac7dd6
echo INSTALL-OK
