#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/app.json
# previous-hash: e8133469c58432ce7ca5e98407dff80081ba20d692a98c6b3cc2cefe159896d7
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json.nuxel-staged
printf '%s  %s\n' e8133469c58432ce7ca5e98407dff80081ba20d692a98c6b3cc2cefe159896d7 /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json | grep -q e8133469c58432ce7ca5e98407dff80081ba20d692a98c6b3cc2cefe159896d7
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/app.json; systemctl restart nuxel-web; fi
