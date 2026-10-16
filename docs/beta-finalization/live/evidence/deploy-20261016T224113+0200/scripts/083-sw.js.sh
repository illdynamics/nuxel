#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/sw.js
# previous-hash: 5fd805e70b8374c4033c6fa682db028fdf693b01fff7e20711b6401ae8c49d86
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js.nuxel-staged
printf '%s  %s\n' 5fd805e70b8374c4033c6fa682db028fdf693b01fff7e20711b6401ae8c49d86 /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/sw.js | grep -q 5fd805e70b8374c4033c6fa682db028fdf693b01fff7e20711b6401ae8c49d86
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
