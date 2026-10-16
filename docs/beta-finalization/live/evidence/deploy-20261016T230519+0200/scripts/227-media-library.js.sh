#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/js/media-library.js
# previous-hash: e70e07def30be16afbad87e94b38133bcccd78db203f82ee5eec9d2c23add521
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js.nuxel-staged
printf '%s  %s\n' e70e07def30be16afbad87e94b38133bcccd78db203f82ee5eec9d2c23add521 /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/js/media-library.js | grep -q e70e07def30be16afbad87e94b38133bcccd78db203f82ee5eec9d2c23add521
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
