#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/bootlog.js
# previous-hash: d2f766a1e3e128fef72389bf99ff43953c0cea7fd54cdf78edd37a612e52ea3b
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-staged
printf '%s  %s\n' d2f766a1e3e128fef72389bf99ff43953c0cea7fd54cdf78edd37a612e52ea3b /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js | grep -q d2f766a1e3e128fef72389bf99ff43953c0cea7fd54cdf78edd37a612e52ea3b
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js; systemctl restart nuxel-web; fi
