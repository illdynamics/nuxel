#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/icons/icon.svg
# previous-hash: a48f7d791325c3747c24b556aa9a19f7dbef62846f7b73594ebea37c49fc0a26
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg.nuxel-staged
printf '%s  %s\n' a48f7d791325c3747c24b556aa9a19f7dbef62846f7b73594ebea37c49fc0a26 /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg | grep -q a48f7d791325c3747c24b556aa9a19f7dbef62846f7b73594ebea37c49fc0a26
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon.svg; systemctl restart nuxel-web; fi
