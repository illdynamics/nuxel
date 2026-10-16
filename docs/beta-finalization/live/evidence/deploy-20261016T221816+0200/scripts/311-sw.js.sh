#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/sw.js
# previous-hash: fc44a84037265202aa621a62cc9733c702c57e2b61d588de17ded4ba50b9a0e7
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js.nuxel-staged
printf '%s  %s\n' fc44a84037265202aa621a62cc9733c702c57e2b61d588de17ded4ba50b9a0e7 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js | grep -q fc44a84037265202aa621a62cc9733c702c57e2b61d588de17ded4ba50b9a0e7
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/sw.js; systemctl restart nuxel-web; fi
