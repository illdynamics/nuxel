#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/console/icons/icon-512.png
# previous-hash: 3b329d853843aeb0dcacd0c648618718986bbda8a2882239cdaeb548fa6bc6af
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png.nuxel-staged
printf '%s  %s\n' 3b329d853843aeb0dcacd0c648618718986bbda8a2882239cdaeb548fa6bc6af /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png | grep -q 3b329d853843aeb0dcacd0c648618718986bbda8a2882239cdaeb548fa6bc6af
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-512.png; systemctl restart nuxel-web; fi
