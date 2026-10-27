#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/js/weather.js
# previous-hash: 69f9b82eb56527b1fd878120bc1de4380d1ab95bae0fcc61c404e45af7b453c3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-staged
printf '%s  %s\n' 69f9b82eb56527b1fd878120bc1de4380d1ab95bae0fcc61c404e45af7b453c3 /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js | grep -q 69f9b82eb56527b1fd878120bc1de4380d1ab95bae0fcc61c404e45af7b453c3
echo INSTALL-OK
