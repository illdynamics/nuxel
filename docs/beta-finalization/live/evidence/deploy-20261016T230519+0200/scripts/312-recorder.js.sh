#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/js/recorder.js
# previous-hash: 929a0c6d285805edf0f192778cb870b26730ce8f8ac68bdfab46aab240954f8d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-staged
printf '%s  %s\n' 929a0c6d285805edf0f192778cb870b26730ce8f8ac68bdfab46aab240954f8d /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js | grep -q 929a0c6d285805edf0f192778cb870b26730ce8f8ac68bdfab46aab240954f8d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
