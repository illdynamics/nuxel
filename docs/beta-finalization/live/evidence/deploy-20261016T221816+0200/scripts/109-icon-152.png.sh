#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/icons/icon-152.png
# previous-hash: 951a9dee84b4d7f6b28f6ef9a4859d64ab1353c980eeaa2d41f18c4fbc5157e6
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png.nuxel-staged
printf '%s  %s\n' 951a9dee84b4d7f6b28f6ef9a4859d64ab1353c980eeaa2d41f18c4fbc5157e6 /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png | grep -q 951a9dee84b4d7f6b28f6ef9a4859d64ab1353c980eeaa2d41f18c4fbc5157e6
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-152.png; systemctl restart nuxel-web; fi
