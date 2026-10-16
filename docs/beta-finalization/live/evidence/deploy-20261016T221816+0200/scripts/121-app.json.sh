#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/app.json
# previous-hash: 0ce9e8295a8e2cb81ec369b7f3e631bd0d031e608dcc39edfff5d922eea19393
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json.nuxel-staged
printf '%s  %s\n' 0ce9e8295a8e2cb81ec369b7f3e631bd0d031e608dcc39edfff5d922eea19393 /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json | grep -q 0ce9e8295a8e2cb81ec369b7f3e631bd0d031e608dcc39edfff5d922eea19393
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/app.json; systemctl restart nuxel-web; fi
