#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/app.json
# previous-hash: 56b76b17b0d1431708fe207d6ee059d277c3bbfd065d040a5c71aa31a4248690
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json.nuxel-staged
printf '%s  %s\n' 56b76b17b0d1431708fe207d6ee059d277c3bbfd065d040a5c71aa31a4248690 /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/app.json | grep -q 56b76b17b0d1431708fe207d6ee059d277c3bbfd065d040a5c71aa31a4248690
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
