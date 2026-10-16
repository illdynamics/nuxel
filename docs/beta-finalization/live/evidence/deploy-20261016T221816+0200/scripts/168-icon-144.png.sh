#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/icons/icon-144.png
# previous-hash: ad1e1c7c5eb8c6d09c9e121c600beb1d66627f61cd211aefa94d06357f1c5dd0
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png.nuxel-staged
printf '%s  %s\n' ad1e1c7c5eb8c6d09c9e121c600beb1d66627f61cd211aefa94d06357f1c5dd0 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png | grep -q ad1e1c7c5eb8c6d09c9e121c600beb1d66627f61cd211aefa94d06357f1c5dd0
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/icons/icon-144.png; systemctl restart nuxel-web; fi
