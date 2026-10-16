#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/js/camera.js
# previous-hash: dbf8f5c9a2ef730b1dc46e5fdd81b492536fb526c5e1b7287bc56123f123962e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js.nuxel-staged
printf '%s  %s\n' dbf8f5c9a2ef730b1dc46e5fdd81b492536fb526c5e1b7287bc56123f123962e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/js/camera.js | grep -q dbf8f5c9a2ef730b1dc46e5fdd81b492536fb526c5e1b7287bc56123f123962e
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
