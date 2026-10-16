#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/recents.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/recents.js
# previous-hash: 7ee9077e7097d118a16ab12af46e0cfe51c0af2a2f4056ef227e21dcd4774214
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/recents.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/recents.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/recents.js /usr/share/nuxel/pwa/nuxel-home/js/recents.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/recents.js.nuxel-staged
printf '%s  %s\n' 7ee9077e7097d118a16ab12af46e0cfe51c0af2a2f4056ef227e21dcd4774214 /usr/share/nuxel/pwa/nuxel-home/js/recents.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/recents.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/recents.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/recents.js | grep -q 7ee9077e7097d118a16ab12af46e0cfe51c0af2a2f4056ef227e21dcd4774214
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/recents.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/recents.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/recents.js; systemctl restart nuxel-web; fi
