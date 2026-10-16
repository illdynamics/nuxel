#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/apps.js
# previous-hash: df08dfaf5d17c3685bee4abb94d24f3f059ed2289edb13bf5159ad162aafcf72
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged
printf '%s  %s\n' df08dfaf5d17c3685bee4abb94d24f3f059ed2289edb13bf5159ad162aafcf72 /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js | grep -q df08dfaf5d17c3685bee4abb94d24f3f059ed2289edb13bf5159ad162aafcf72
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/apps.js; systemctl restart nuxel-web; fi
