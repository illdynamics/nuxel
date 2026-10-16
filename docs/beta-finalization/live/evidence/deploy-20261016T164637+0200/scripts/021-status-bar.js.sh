#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/status-bar.js
# previous-hash: 7a2f02eacff1fe904c73ad631d1882406c4a9c9d4512e9cfceee6f4ff6606723
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged
printf '%s  %s\n' 7a2f02eacff1fe904c73ad631d1882406c4a9c9d4512e9cfceee6f4ff6606723 /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js | grep -q 7a2f02eacff1fe904c73ad631d1882406c4a9c9d4512e9cfceee6f4ff6606723
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/status-bar.js; systemctl restart nuxel-web; fi
