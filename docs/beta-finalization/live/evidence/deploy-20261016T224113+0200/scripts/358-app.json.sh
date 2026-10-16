#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/terminal/app.json
# previous-hash: 268a15213e86e1622be46c4abc769a7608e2d12fefa7b6b0c3e5cb5489fbe103
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json.nuxel-staged
printf '%s  %s\n' 268a15213e86e1622be46c4abc769a7608e2d12fefa7b6b0c3e5cb5489fbe103 /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/app.json | grep -q 268a15213e86e1622be46c4abc769a7608e2d12fefa7b6b0c3e5cb5489fbe103
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
