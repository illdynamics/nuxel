#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/files/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/sw.js
# previous-hash: 0d04e531f89280f25aa6a247f4b990717a1d4b4470c97d204f42cc69197e5bbb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/files/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/sw.js /usr/share/nuxel/pwa/nuxel-apps/files/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/sw.js.nuxel-staged
printf '%s  %s\n' 0d04e531f89280f25aa6a247f4b990717a1d4b4470c97d204f42cc69197e5bbb /usr/share/nuxel/pwa/nuxel-apps/files/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/sw.js | grep -q 0d04e531f89280f25aa6a247f4b990717a1d4b4470c97d204f42cc69197e5bbb
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
