#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/penguinterface/icons/icon-192.png
# previous-hash: 11b30f919c37e1396132977ec20330e242558cd77f21a573f60e242738fb3b79
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png.nuxel-staged
printf '%s  %s\n' 11b30f919c37e1396132977ec20330e242558cd77f21a573f60e242738fb3b79 /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png | grep -q 11b30f919c37e1396132977ec20330e242558cd77f21a573f60e242738fb3b79
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/penguinterface/icons/icon-192.png; systemctl restart nuxel-web; fi
