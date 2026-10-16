#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/js/vault.js
# previous-hash: 251e0925e7d2ed73a3513930201b8f82850ff48c6d7cfdfa6707bbfbd96fa6ea
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js.nuxel-staged
printf '%s  %s\n' 251e0925e7d2ed73a3513930201b8f82850ff48c6d7cfdfa6707bbfbd96fa6ea /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js | grep -q 251e0925e7d2ed73a3513930201b8f82850ff48c6d7cfdfa6707bbfbd96fa6ea
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/js/vault.js; systemctl restart nuxel-web; fi
