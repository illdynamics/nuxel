#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/maps/js/maps.js
# previous-hash: 4190a630e7bf5bd9ee0583f2d4810ffc98a38fd44ab1232d16e82091c5bb4589
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-staged
printf '%s  %s\n' 4190a630e7bf5bd9ee0583f2d4810ffc98a38fd44ab1232d16e82091c5bb4589 /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js | grep -q 4190a630e7bf5bd9ee0583f2d4810ffc98a38fd44ab1232d16e82091c5bb4589
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
