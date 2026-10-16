#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/photos/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/app.json
# previous-hash: 9b0b0ecf56c2c44cfe3866b0bb351fe1231b016839b8e03dffb62b1aef2a3fd5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/photos/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/app.json /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-staged
printf '%s  %s\n' 9b0b0ecf56c2c44cfe3866b0bb351fe1231b016839b8e03dffb62b1aef2a3fd5 /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/app.json | grep -q 9b0b0ecf56c2c44cfe3866b0bb351fe1231b016839b8e03dffb62b1aef2a3fd5
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
