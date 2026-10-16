#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/index.html
# previous-hash: b8a5a3d5e141d692d6d499891e961bccba937be22a014e3d8404c6ca10ec4ccd
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-staged
printf '%s  %s\n' b8a5a3d5e141d692d6d499891e961bccba937be22a014e3d8404c6ca10ec4ccd /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html | grep -q b8a5a3d5e141d692d6d499891e961bccba937be22a014e3d8404c6ca10ec4ccd
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html; systemctl restart nuxel-web; fi
