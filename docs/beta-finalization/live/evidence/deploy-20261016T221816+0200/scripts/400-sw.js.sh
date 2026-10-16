#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/terminal/sw.js
# previous-hash: a0783f475b6be9845450b6b083430e9db89f07acdbfd9035206ae4b660dda01c
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js.nuxel-staged
printf '%s  %s\n' a0783f475b6be9845450b6b083430e9db89f07acdbfd9035206ae4b660dda01c /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js | grep -q a0783f475b6be9845450b6b083430e9db89f07acdbfd9035206ae4b660dda01c
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/terminal/sw.js; systemctl restart nuxel-web; fi
