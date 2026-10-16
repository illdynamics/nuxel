#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/bridge.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/bridge.js
# previous-hash: 6a02998c715be597f3150192207e7e10f7907e2ae729ad88efb7daa8fb308d00
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/bridge.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bridge.js /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged
printf '%s  %s\n' 6a02998c715be597f3150192207e7e10f7907e2ae729ad88efb7daa8fb308d00 /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bridge.js | grep -q 6a02998c715be597f3150192207e7e10f7907e2ae729ad88efb7daa8fb308d00
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
