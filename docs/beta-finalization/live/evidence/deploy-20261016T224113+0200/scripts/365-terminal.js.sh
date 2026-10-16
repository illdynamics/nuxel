#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/terminal/terminal.js
# previous-hash: e210d4f27aca5885cbf8ab4e598dc166a58ceef8808cdb4f9be74620cbc71c82
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js.nuxel-staged
printf '%s  %s\n' e210d4f27aca5885cbf8ab4e598dc166a58ceef8808cdb4f9be74620cbc71c82 /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/terminal.js | grep -q e210d4f27aca5885cbf8ab4e598dc166a58ceef8808cdb4f9be74620cbc71c82
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
