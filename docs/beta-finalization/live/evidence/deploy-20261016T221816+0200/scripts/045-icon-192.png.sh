#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/icons/icon-192.png
# previous-hash: f9272726f363e51ddd73cc5f7eb5951bde2dd4d54213a6df2196884cdccf7fff
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png.nuxel-staged
printf '%s  %s\n' f9272726f363e51ddd73cc5f7eb5951bde2dd4d54213a6df2196884cdccf7fff /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png | grep -q f9272726f363e51ddd73cc5f7eb5951bde2dd4d54213a6df2196884cdccf7fff
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-192.png; systemctl restart nuxel-web; fi
