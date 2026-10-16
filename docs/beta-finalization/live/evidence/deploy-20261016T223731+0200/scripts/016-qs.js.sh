#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/qs.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/qs.js
# previous-hash: 2391b5683361415cefbfdb7465457b813fd7f5a320a5662fa6030147642c1777
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/qs.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/qs.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/qs.js /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged
printf '%s  %s\n' 2391b5683361415cefbfdb7465457b813fd7f5a320a5662fa6030147642c1777 /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/qs.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/qs.js | grep -q 2391b5683361415cefbfdb7465457b813fd7f5a320a5662fa6030147642c1777
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
