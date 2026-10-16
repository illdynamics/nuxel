#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/js/rootcontrol.js
# previous-hash: fb8d6a59dff00c10a4d5345ec47999d9cdc4475e3c404a47bb74016e47a4eb47
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-staged
printf '%s  %s\n' fb8d6a59dff00c10a4d5345ec47999d9cdc4475e3c404a47bb74016e47a4eb47 /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js | grep -q fb8d6a59dff00c10a4d5345ec47999d9cdc4475e3c404a47bb74016e47a4eb47
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js; systemctl restart nuxel-web; fi
