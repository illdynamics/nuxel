#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/power-menu.js
# previous-hash: 466e768c0a3a174584db62c67b072d3b4e910acab8697b36b8db3fa150c0a40a
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged
printf '%s  %s\n' 466e768c0a3a174584db62c67b072d3b4e910acab8697b36b8db3fa150c0a40a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js | grep -q 466e768c0a3a174584db62c67b072d3b4e910acab8697b36b8db3fa150c0a40a
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js; systemctl restart nuxel-web; fi
