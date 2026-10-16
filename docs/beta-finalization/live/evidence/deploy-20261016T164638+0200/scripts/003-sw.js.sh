#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/sw.js
# previous-hash: e259bd53882c29857a492272d466a5b3b6168c32f619ba38fd37a16690970f9b
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/sw.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/sw.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/sw.js /home/nuxel/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/sw.js.nuxel-staged
printf '%s  %s\n' e259bd53882c29857a492272d466a5b3b6168c32f619ba38fd37a16690970f9b /home/nuxel/nuxel/pwa/nuxel-home/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/sw.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/sw.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/sw.js | grep -q e259bd53882c29857a492272d466a5b3b6168c32f619ba38fd37a16690970f9b
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/sw.js; systemctl restart nuxel-web; fi
