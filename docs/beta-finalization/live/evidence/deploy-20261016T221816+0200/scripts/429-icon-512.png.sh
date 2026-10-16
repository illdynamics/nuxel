#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/icons/icon-512.png
# previous-hash: 3f72dea12870fe315349d24aac0326fb1352f38756682253b99a9276f0da248f
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-staged
printf '%s  %s\n' 3f72dea12870fe315349d24aac0326fb1352f38756682253b99a9276f0da248f /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png | grep -q 3f72dea12870fe315349d24aac0326fb1352f38756682253b99a9276f0da248f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/bridge.js)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/icons/icon-512.png; systemctl restart nuxel-web; fi
