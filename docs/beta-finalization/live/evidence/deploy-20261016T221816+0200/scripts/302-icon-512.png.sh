#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/icons/icon-512.png
# previous-hash: c24ff4d15e8c8c5dd09d52aa05872ddcdba186084ac29e9ff899a33fd6293973
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png.nuxel-staged
printf '%s  %s\n' c24ff4d15e8c8c5dd09d52aa05872ddcdba186084ac29e9ff899a33fd6293973 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png | grep -q c24ff4d15e8c8c5dd09d52aa05872ddcdba186084ac29e9ff899a33fd6293973
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-512.png; systemctl restart nuxel-web; fi
