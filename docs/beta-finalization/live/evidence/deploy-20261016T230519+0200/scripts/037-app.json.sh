#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calculator/app.json
# previous-hash: 191b60786c8b4ce8f7fa9915f869b1ffd94aa44793bf7f208359a9626b32ac96
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json.nuxel-staged
printf '%s  %s\n' 191b60786c8b4ce8f7fa9915f869b1ffd94aa44793bf7f208359a9626b32ac96 /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/app.json | grep -q 191b60786c8b4ce8f7fa9915f869b1ffd94aa44793bf7f208359a9626b32ac96
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
