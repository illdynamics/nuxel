#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/css/photos.css
# previous-hash: 576b27e7b731f936effa845b31c2f3ebf83d61fa6a81b9bf2f1312dfe325f9f1
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css.nuxel-staged
printf '%s  %s\n' 576b27e7b731f936effa845b31c2f3ebf83d61fa6a81b9bf2f1312dfe325f9f1 /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css | grep -q 576b27e7b731f936effa845b31c2f3ebf83d61fa6a81b9bf2f1312dfe325f9f1
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/photos/css/photos.css; systemctl restart nuxel-web; fi
