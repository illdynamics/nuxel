#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/js/snekbyte.js
# previous-hash: 3faea1a33f06d93c2b7365a8d7832199dbd6a84cf79818e25209a5405c16b5eb
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-staged
printf '%s  %s\n' 3faea1a33f06d93c2b7365a8d7832199dbd6a84cf79818e25209a5405c16b5eb /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js | grep -q 3faea1a33f06d93c2b7365a8d7832199dbd6a84cf79818e25209a5405c16b5eb
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js; systemctl restart nuxel-web; fi
