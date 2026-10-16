#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/js/downloader.js
# previous-hash: 646921f789ba4a2c4e1a66f28bda0ddd62fbdddb2460a54a8e47ccb7ecc89256
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js.nuxel-staged
printf '%s  %s\n' 646921f789ba4a2c4e1a66f28bda0ddd62fbdddb2460a54a8e47ccb7ecc89256 /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/js/downloader.js | grep -q 646921f789ba4a2c4e1a66f28bda0ddd62fbdddb2460a54a8e47ccb7ecc89256
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
