#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/touch-keyboard.js
# previous-hash: 75584275ad75d65200b77b9ba5d637421c7c4c8487a61260408436c3d9a210f9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged
printf '%s  %s\n' 75584275ad75d65200b77b9ba5d637421c7c4c8487a61260408436c3d9a210f9 /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js | grep -q 75584275ad75d65200b77b9ba5d637421c7c4c8487a61260408436c3d9a210f9
echo INSTALL-OK
