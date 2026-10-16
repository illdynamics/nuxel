#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/icons/icon-384.png
# previous-hash: 0c5705eaea6dc26e38622b440f1fadbef85ffff47500c8ad5b3700aec6d76b83
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png.nuxel-staged
printf '%s  %s\n' 0c5705eaea6dc26e38622b440f1fadbef85ffff47500c8ad5b3700aec6d76b83 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png | grep -q 0c5705eaea6dc26e38622b440f1fadbef85ffff47500c8ad5b3700aec6d76b83
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-384.png; systemctl restart nuxel-web; fi
