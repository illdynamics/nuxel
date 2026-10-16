#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/js/files.js
# previous-hash: abb59eb3124fb7ea7a73e807bb0be028500fdbae040d8a0ea3fc31a7c0abc97f
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-staged
printf '%s  %s\n' abb59eb3124fb7ea7a73e807bb0be028500fdbae040d8a0ea3fc31a7c0abc97f /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js | grep -q abb59eb3124fb7ea7a73e807bb0be028500fdbae040d8a0ea3fc31a7c0abc97f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/files/js/files.js; systemctl restart nuxel-web; fi
