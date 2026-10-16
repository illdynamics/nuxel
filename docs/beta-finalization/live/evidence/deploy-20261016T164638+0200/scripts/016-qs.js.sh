#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/qs.js
# previous-hash: ea8b4cafc0517226e5163bd77d759ada465cf3cdb9d3d3eb0ed24458572ca4ea
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged
printf '%s  %s\n' ea8b4cafc0517226e5163bd77d759ada465cf3cdb9d3d3eb0ed24458572ca4ea /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js | grep -q ea8b4cafc0517226e5163bd77d759ada465cf3cdb9d3d3eb0ed24458572ca4ea
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/qs.js; systemctl restart nuxel-web; fi
