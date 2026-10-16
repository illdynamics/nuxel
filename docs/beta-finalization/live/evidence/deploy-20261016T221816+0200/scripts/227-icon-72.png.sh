#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/icons/icon-72.png
# previous-hash: 51a374a0b788f1af0f804e08860bd0f15af9ef09cc6264ae7f5ff1db015cea99
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png.nuxel-staged
printf '%s  %s\n' 51a374a0b788f1af0f804e08860bd0f15af9ef09cc6264ae7f5ff1db015cea99 /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png | grep -q 51a374a0b788f1af0f804e08860bd0f15af9ef09cc6264ae7f5ff1db015cea99
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-72.png; systemctl restart nuxel-web; fi
