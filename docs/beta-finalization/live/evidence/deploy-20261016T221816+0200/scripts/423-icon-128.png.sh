#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/icons/icon-128.png
# previous-hash: 10e4414ee469b24878aab53efe3c62ef60975b793ae672eeb9d3f5d156334171
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' 10e4414ee469b24878aab53efe3c62ef60975b793ae672eeb9d3f5d156334171 /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png | grep -q 10e4414ee469b24878aab53efe3c62ef60975b793ae672eeb9d3f5d156334171
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/bridge.js)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/icons/icon-128.png; systemctl restart nuxel-web; fi
