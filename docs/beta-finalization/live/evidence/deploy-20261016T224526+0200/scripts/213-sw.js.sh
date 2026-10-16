#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/maps/sw.js
# previous-hash: d2ec2ba17c6b1b04380511dd0ba332da4c17f01cf4aa292b56eef0445b782f54
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-staged
printf '%s  %s\n' d2ec2ba17c6b1b04380511dd0ba332da4c17f01cf4aa292b56eef0445b782f54 /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js | grep -q d2ec2ba17c6b1b04380511dd0ba332da4c17f01cf4aa292b56eef0445b782f54
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
