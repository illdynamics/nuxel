#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/js/notes.js
# previous-hash: 4d23fd89a68b3dffc7ae7fe24f97edec21c2f082759bcfcc1a91d2716b38655c
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-staged
printf '%s  %s\n' 4d23fd89a68b3dffc7ae7fe24f97edec21c2f082759bcfcc1a91d2716b38655c /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js | grep -q 4d23fd89a68b3dffc7ae7fe24f97edec21c2f082759bcfcc1a91d2716b38655c
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js; systemctl restart nuxel-web; fi
