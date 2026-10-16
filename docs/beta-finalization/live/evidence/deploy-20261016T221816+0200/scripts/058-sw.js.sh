#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/sw.js
# previous-hash: b4b38adf4eeea7d0155ea46d7094044360ea680c9676242d4fa11422464a8540
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js.nuxel-staged
printf '%s  %s\n' b4b38adf4eeea7d0155ea46d7094044360ea680c9676242d4fa11422464a8540 /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js | grep -q b4b38adf4eeea7d0155ea46d7094044360ea680c9676242d4fa11422464a8540
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/sw.js; systemctl restart nuxel-web; fi
