#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/js/totp.js
# previous-hash: 2671d35ace9b39ac1c53319540326ef14fb0c7bf0297e414624e8269854d88e1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js.nuxel-staged
printf '%s  %s\n' 2671d35ace9b39ac1c53319540326ef14fb0c7bf0297e414624e8269854d88e1 /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/totp.js | grep -q 2671d35ace9b39ac1c53319540326ef14fb0c7bf0297e414624e8269854d88e1
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
