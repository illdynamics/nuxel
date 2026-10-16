#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/bridge.js
# previous-hash: 6a02998c715be597f3150192207e7e10f7907e2ae729ad88efb7daa8fb308d00
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged
printf '%s  %s\n' 6a02998c715be597f3150192207e7e10f7907e2ae729ad88efb7daa8fb308d00 /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js | grep -q 6a02998c715be597f3150192207e7e10f7907e2ae729ad88efb7daa8fb308d00
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/bridge.js; systemctl restart nuxel-web; fi
