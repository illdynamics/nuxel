#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/settings-store.js
# previous-hash: a53818e9605b055c3dfbfac4a1401896c94f7e94fb87acc958173b30f47abfde
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged
printf '%s  %s\n' a53818e9605b055c3dfbfac4a1401896c94f7e94fb87acc958173b30f47abfde /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js | grep -q a53818e9605b055c3dfbfac4a1401896c94f7e94fb87acc958173b30f47abfde
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/settings-store.js; systemctl restart nuxel-web; fi
