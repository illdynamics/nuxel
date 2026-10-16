#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/host-bridge.js
# previous-hash: 0eff4202110720b77c7702439709fc06e74dd9e5a31cff4884fb8418d088ab5c
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged
printf '%s  %s\n' 0eff4202110720b77c7702439709fc06e74dd9e5a31cff4884fb8418d088ab5c /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js | grep -q 0eff4202110720b77c7702439709fc06e74dd9e5a31cff4884fb8418d088ab5c
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js; systemctl restart nuxel-web; fi
