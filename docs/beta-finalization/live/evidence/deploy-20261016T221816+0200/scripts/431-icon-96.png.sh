#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/icons/icon-96.png
# previous-hash: de2227e0254065590ff0171b773d0ab111fe9e9fc0668337b211ac84d59b49b5
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png.nuxel-staged
printf '%s  %s\n' de2227e0254065590ff0171b773d0ab111fe9e9fc0668337b211ac84d59b49b5 /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png | grep -q de2227e0254065590ff0171b773d0ab111fe9e9fc0668337b211ac84d59b49b5
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/bridge.js)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/icons/icon-96.png; systemctl restart nuxel-web; fi
