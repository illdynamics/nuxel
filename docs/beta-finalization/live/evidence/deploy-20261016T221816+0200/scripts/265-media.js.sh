#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/js/media.js
# previous-hash: ee325b07cc45c14aba4c4477350f51f6ce3fa71316e4f76ad4adfbb04feb09ad
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js.nuxel-staged
printf '%s  %s\n' ee325b07cc45c14aba4c4477350f51f6ce3fa71316e4f76ad4adfbb04feb09ad /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js | grep -q ee325b07cc45c14aba4c4477350f51f6ce3fa71316e4f76ad4adfbb04feb09ad
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/js/media.js; systemctl restart nuxel-web; fi
