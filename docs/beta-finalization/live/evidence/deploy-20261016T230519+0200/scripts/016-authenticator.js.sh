#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/js/authenticator.js
# previous-hash: da07e9c47ee933c052468d7545e7a8826364a807fa2be00c52aafb83566e2468
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js.nuxel-staged
printf '%s  %s\n' da07e9c47ee933c052468d7545e7a8826364a807fa2be00c52aafb83566e2468 /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/authenticator.js | grep -q da07e9c47ee933c052468d7545e7a8826364a807fa2be00c52aafb83566e2468
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
