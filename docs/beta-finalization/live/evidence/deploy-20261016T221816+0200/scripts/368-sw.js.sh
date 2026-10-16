#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/sw.js
# previous-hash: 92e0126ab5afe5104f08b7cfa47b0f9763b389401c8fc87d3e9e3a8d2cc63839
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js.nuxel-staged
printf '%s  %s\n' 92e0126ab5afe5104f08b7cfa47b0f9763b389401c8fc87d3e9e3a8d2cc63839 /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js | grep -q 92e0126ab5afe5104f08b7cfa47b0f9763b389401c8fc87d3e9e3a8d2cc63839
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/sw.js; systemctl restart nuxel-web; fi
