#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/app.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/app.js
# previous-hash: 2ba9ff8be5331b18ba0353a95ddace87edb8c4f7f368c6ca17f3113ace2d849a
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/app.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged
printf '%s  %s\n' 2ba9ff8be5331b18ba0353a95ddace87edb8c4f7f368c6ca17f3113ace2d849a /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/app.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | grep -q 2ba9ff8be5331b18ba0353a95ddace87edb8c4f7f368c6ca17f3113ace2d849a
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/app.js; systemctl restart nuxel-web; fi
