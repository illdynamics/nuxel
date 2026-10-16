#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/icons/icon.svg
# previous-hash: 84269bdeebab535d1d6c7b2345c1aa04514e49d3ec115b6f7132a33ef1495e47
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg.nuxel-staged
printf '%s  %s\n' 84269bdeebab535d1d6c7b2345c1aa04514e49d3ec115b6f7132a33ef1495e47 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg | grep -q 84269bdeebab535d1d6c7b2345c1aa04514e49d3ec115b6f7132a33ef1495e47
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon.svg; systemctl restart nuxel-web; fi
