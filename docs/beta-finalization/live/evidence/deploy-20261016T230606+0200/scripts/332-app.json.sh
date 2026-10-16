#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/app.json
# previous-hash: f98e3a070b3748abd6e88d84a4cf63b17968a261e7042694f56c0e4d6905df80
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/app.json /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-staged
printf '%s  %s\n' f98e3a070b3748abd6e88d84a4cf63b17968a261e7042694f56c0e4d6905df80 /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/app.json | grep -q f98e3a070b3748abd6e88d84a4cf63b17968a261e7042694f56c0e4d6905df80
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
