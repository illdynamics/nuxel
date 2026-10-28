#!/bin/sh
# Disable DOM keyboard fallback when Stevia provider is present; bump PWA cache -> /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/touch-keyboard.js
# previous-hash: 725f6bc00ce14120dc2bc131d862d420e17d59183b1a1f89da2bfa35cdb79d94
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261028T101758-2799662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261028T101758-2799662 /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261028T101758-2799662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-rollback.pre-deploy-20261028T101758-2799662; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged
printf '%s  %s\n' 725f6bc00ce14120dc2bc131d862d420e17d59183b1a1f89da2bfa35cdb79d94 /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/touch-keyboard.js | grep -q 725f6bc00ce14120dc2bc131d862d420e17d59183b1a1f89da2bfa35cdb79d94
echo INSTALL-OK
