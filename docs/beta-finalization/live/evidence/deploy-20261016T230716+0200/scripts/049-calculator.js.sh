#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calculator/js/calculator.js
# previous-hash: 2d36e8278ea24a60fa31a76490636036ead82455a7ca07e8fe3802063e86c613
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js.nuxel-staged
printf '%s  %s\n' 2d36e8278ea24a60fa31a76490636036ead82455a7ca07e8fe3802063e86c613 /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/js/calculator.js | grep -q 2d36e8278ea24a60fa31a76490636036ead82455a7ca07e8fe3802063e86c613
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
