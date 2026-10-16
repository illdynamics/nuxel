#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/icons/icon-144.png
# previous-hash: ea5d25b4eac3b669e2bbcb0f9b7a436897f5e3e313a98fd7ae7f4cf03022a580
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png.nuxel-staged
printf '%s  %s\n' ea5d25b4eac3b669e2bbcb0f9b7a436897f5e3e313a98fd7ae7f4cf03022a580 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png | grep -q ea5d25b4eac3b669e2bbcb0f9b7a436897f5e3e313a98fd7ae7f4cf03022a580
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-144.png; systemctl restart nuxel-web; fi
