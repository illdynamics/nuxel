#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/icons/icon-152.png
# previous-hash: 07de2231aafeb0c0d0284c7f39a1456b95c44199f29a52f58c76fee299ef00d7
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png.nuxel-staged
printf '%s  %s\n' 07de2231aafeb0c0d0284c7f39a1456b95c44199f29a52f58c76fee299ef00d7 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png | grep -q 07de2231aafeb0c0d0284c7f39a1456b95c44199f29a52f58c76fee299ef00d7
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/icons/icon-152.png; systemctl restart nuxel-web; fi
