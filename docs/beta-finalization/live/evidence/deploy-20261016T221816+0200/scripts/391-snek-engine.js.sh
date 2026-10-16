#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/js/snek-engine.js
# previous-hash: f1028ceff2ff923e85b1679c458640b0e4d677388d2b0ee761666efd4a3d7c3e
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js.nuxel-staged
printf '%s  %s\n' f1028ceff2ff923e85b1679c458640b0e4d677388d2b0ee761666efd4a3d7c3e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js | grep -q f1028ceff2ff923e85b1679c458640b0e4d677388d2b0ee761666efd4a3d7c3e
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snek-engine.js; systemctl restart nuxel-web; fi
