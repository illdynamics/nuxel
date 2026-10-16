#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/icons/icon-72.png
# previous-hash: ff09d58e559701876812ce6ac2a3ffaa72114d3f5c07fc8c06be55c78e2fa1c5
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png.nuxel-staged
printf '%s  %s\n' ff09d58e559701876812ce6ac2a3ffaa72114d3f5c07fc8c06be55c78e2fa1c5 /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png | grep -q ff09d58e559701876812ce6ac2a3ffaa72114d3f5c07fc8c06be55c78e2fa1c5
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-72.png; systemctl restart nuxel-web; fi
