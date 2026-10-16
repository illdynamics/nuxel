#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/recents.js
# previous-hash: 7ee9077e7097d118a16ab12af46e0cfe51c0af2a2f4056ef227e21dcd4774214
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js.nuxel-staged
printf '%s  %s\n' 7ee9077e7097d118a16ab12af46e0cfe51c0af2a2f4056ef227e21dcd4774214 /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js | grep -q 7ee9077e7097d118a16ab12af46e0cfe51c0af2a2f4056ef227e21dcd4774214
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/js/recents.js; systemctl restart nuxel-web; fi
