#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/search.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/search.js
# previous-hash: 49c60d37b0e66d2feb1f233fbc2d9f2b49e76b115337a4584518727c5d1f677d
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/search.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/search.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/search.js /home/nuxel/nuxel/pwa/nuxel-home/js/search.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/search.js.nuxel-staged
printf '%s  %s\n' 49c60d37b0e66d2feb1f233fbc2d9f2b49e76b115337a4584518727c5d1f677d /home/nuxel/nuxel/pwa/nuxel-home/js/search.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/search.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/search.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/search.js | grep -q 49c60d37b0e66d2feb1f233fbc2d9f2b49e76b115337a4584518727c5d1f677d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/search.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/search.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/search.js; systemctl restart nuxel-web; fi
