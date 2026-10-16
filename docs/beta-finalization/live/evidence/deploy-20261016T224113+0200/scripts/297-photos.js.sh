#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/js/photos.js
# previous-hash: b510723a616034e2d495c25d753f981725bc592e29bcba95e3717ddd8cf94902
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js.nuxel-staged
printf '%s  %s\n' b510723a616034e2d495c25d753f981725bc592e29bcba95e3717ddd8cf94902 /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/js/photos.js | grep -q b510723a616034e2d495c25d753f981725bc592e29bcba95e3717ddd8cf94902
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
