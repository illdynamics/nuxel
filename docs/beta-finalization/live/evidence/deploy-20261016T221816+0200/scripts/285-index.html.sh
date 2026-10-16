#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/index.html
# previous-hash: 247f4c173cef0c9f81a7e99a84f9568aa089056c868254871dcd7e3064087c7b
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/index.html /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged
printf '%s  %s\n' 247f4c173cef0c9f81a7e99a84f9568aa089056c868254871dcd7e3064087c7b /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/index.html | grep -q 247f4c173cef0c9f81a7e99a84f9568aa089056c868254871dcd7e3064087c7b
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/index.html; systemctl restart nuxel-web; fi
