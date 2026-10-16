#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/app.json
# previous-hash: af5b9a70ad952910786ee33eff7cba3e5f8fabb92041ca8708fb5c79175b9400
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/app.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/app.json /usr/share/nuxel/pwa/nuxel-apps/notes/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/app.json.nuxel-staged
printf '%s  %s\n' af5b9a70ad952910786ee33eff7cba3e5f8fabb92041ca8708fb5c79175b9400 /usr/share/nuxel/pwa/nuxel-apps/notes/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/app.json | grep -q af5b9a70ad952910786ee33eff7cba3e5f8fabb92041ca8708fb5c79175b9400
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/app.json; systemctl restart nuxel-web; fi
