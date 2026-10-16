#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/launcher.js
# previous-hash: 3dc737d867a2ad31a10c4a1f8a472b77e78b76a7065a6b34b88be3dd88c91346
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged
printf '%s  %s\n' 3dc737d867a2ad31a10c4a1f8a472b77e78b76a7065a6b34b88be3dd88c91346 /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js | grep -q 3dc737d867a2ad31a10c4a1f8a472b77e78b76a7065a6b34b88be3dd88c91346
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/launcher.js; systemctl restart nuxel-web; fi
