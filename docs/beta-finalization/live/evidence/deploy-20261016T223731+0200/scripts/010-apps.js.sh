#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/apps.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/apps.js
# previous-hash: df08dfaf5d17c3685bee4abb94d24f3f059ed2289edb13bf5159ad162aafcf72
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/apps.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/apps.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged
printf '%s  %s\n' df08dfaf5d17c3685bee4abb94d24f3f059ed2289edb13bf5159ad162aafcf72 /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/apps.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js | grep -q df08dfaf5d17c3685bee4abb94d24f3f059ed2289edb13bf5159ad162aafcf72
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
