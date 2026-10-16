#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-common/geolocation.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/geolocation.js
# previous-hash: c451b588240022537ca2ff29d8c2eb301b18dfad388f0dbfeda6306280980d64
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/geolocation.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/geolocation.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-common/geolocation.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/geolocation.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/geolocation.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/geolocation.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/geolocation.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/geolocation.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/geolocation.js /usr/share/nuxel/pwa/nuxel-common/geolocation.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-common/geolocation.js.nuxel-staged
printf '%s  %s\n' c451b588240022537ca2ff29d8c2eb301b18dfad388f0dbfeda6306280980d64 /usr/share/nuxel/pwa/nuxel-common/geolocation.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/geolocation.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/geolocation.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/geolocation.js | grep -q c451b588240022537ca2ff29d8c2eb301b18dfad388f0dbfeda6306280980d64
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/bridge.js)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
echo INSTALL-OK
