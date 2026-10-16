#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/js/storage.js
# previous-hash: a6c17a60b900257adc2937d4fe93def8ae94c4b7bcd3d15e852ab152e999ea08
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js.nuxel-staged
printf '%s  %s\n' a6c17a60b900257adc2937d4fe93def8ae94c4b7bcd3d15e852ab152e999ea08 /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/js/storage.js | grep -q a6c17a60b900257adc2937d4fe93def8ae94c4b7bcd3d15e852ab152e999ea08
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
