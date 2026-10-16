#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/browser/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/browser/app.json
# previous-hash: 5ee7f7395e47199a92e9fe8308fd83d5f05b7b7bfdb7c8043ece68c7dddf1b95
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/browser/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/browser/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/browser/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/app.json /usr/share/nuxel/pwa/nuxel-apps/browser/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/browser/app.json.nuxel-staged
printf '%s  %s\n' 5ee7f7395e47199a92e9fe8308fd83d5f05b7b7bfdb7c8043ece68c7dddf1b95 /usr/share/nuxel/pwa/nuxel-apps/browser/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/browser/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/browser/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/app.json | grep -q 5ee7f7395e47199a92e9fe8308fd83d5f05b7b7bfdb7c8043ece68c7dddf1b95
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
