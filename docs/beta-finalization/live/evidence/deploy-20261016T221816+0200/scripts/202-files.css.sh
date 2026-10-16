#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/css/files.css
# previous-hash: 3418757fc1bea072ccbe353a0ffa52c66466ad8e447cdb07ac30cd6d5d3d541c
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged
printf '%s  %s\n' 3418757fc1bea072ccbe353a0ffa52c66466ad8e447cdb07ac30cd6d5d3d541c /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css | grep -q 3418757fc1bea072ccbe353a0ffa52c66466ad8e447cdb07ac30cd6d5d3d541c
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/files/css/files.css; systemctl restart nuxel-web; fi
