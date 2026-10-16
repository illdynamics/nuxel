#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/js/weather.js
# previous-hash: ff706045732ae0ffb604a9792b57e4c15c3c7a1e4a7b29cde675626588edc675
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-staged
printf '%s  %s\n' ff706045732ae0ffb604a9792b57e4c15c3c7a1e4a7b29cde675626588edc675 /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/js/weather.js | grep -q ff706045732ae0ffb604a9792b57e4c15c3c7a1e4a7b29cde675626588edc675
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
