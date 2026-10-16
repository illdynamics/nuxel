#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/safe-zones.js
# previous-hash: 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged
printf '%s  %s\n' 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js | grep -q 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/safe-zones.js; systemctl restart nuxel-web; fi
