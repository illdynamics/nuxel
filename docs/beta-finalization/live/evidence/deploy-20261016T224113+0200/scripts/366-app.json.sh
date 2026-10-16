#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/weather/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/app.json
# previous-hash: e2c4c8e044d40e9b501a0b99324da7381e6563651d5b3805923a76d1c12204a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/weather/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/app.json /usr/share/nuxel/pwa/nuxel-apps/weather/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/app.json.nuxel-staged
printf '%s  %s\n' e2c4c8e044d40e9b501a0b99324da7381e6563651d5b3805923a76d1c12204a0 /usr/share/nuxel/pwa/nuxel-apps/weather/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/app.json | grep -q e2c4c8e044d40e9b501a0b99324da7381e6563651d5b3805923a76d1c12204a0
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
