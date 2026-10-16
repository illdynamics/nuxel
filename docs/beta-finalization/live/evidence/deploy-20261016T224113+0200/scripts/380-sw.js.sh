#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/sw.js
# previous-hash: de9da8342e62afb071e34f168ef89844aef36c4661d61991c284c8e0be10f744
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js.nuxel-staged
printf '%s  %s\n' de9da8342e62afb071e34f168ef89844aef36c4661d61991c284c8e0be10f744 /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/sw.js | grep -q de9da8342e62afb071e34f168ef89844aef36c4661d61991c284c8e0be10f744
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
