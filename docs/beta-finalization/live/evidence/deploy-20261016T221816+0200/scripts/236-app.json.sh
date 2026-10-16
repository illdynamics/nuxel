#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/maps/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/maps/app.json
# previous-hash: 2739662910680288c26172f43a92ac388d7cb4d43bf4b1bf9e5c3983cfd02e81
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/app.json /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-staged
printf '%s  %s\n' 2739662910680288c26172f43a92ac388d7cb4d43bf4b1bf9e5c3983cfd02e81 /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/app.json | grep -q 2739662910680288c26172f43a92ac388d7cb4d43bf4b1bf9e5c3983cfd02e81
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/maps/app.json; systemctl restart nuxel-web; fi
