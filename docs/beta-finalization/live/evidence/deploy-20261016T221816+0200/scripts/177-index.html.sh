#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/index.html
# previous-hash: 4b8932499ce0c4e94d55844159fc5332f06396e321463dfde6266762e1031089
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html.nuxel-staged
printf '%s  %s\n' 4b8932499ce0c4e94d55844159fc5332f06396e321463dfde6266762e1031089 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html | grep -q 4b8932499ce0c4e94d55844159fc5332f06396e321463dfde6266762e1031089
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/index.html; systemctl restart nuxel-web; fi
