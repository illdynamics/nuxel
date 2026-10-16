#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/manifest.json
# previous-hash: 7be32f63cae57fd380d60a43d90ec114b0fd1bab2152ffac31d1581f7c4849d1
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json.nuxel-staged
printf '%s  %s\n' 7be32f63cae57fd380d60a43d90ec114b0fd1bab2152ffac31d1581f7c4849d1 /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json | grep -q 7be32f63cae57fd380d60a43d90ec114b0fd1bab2152ffac31d1581f7c4849d1
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/manifest.json; systemctl restart nuxel-web; fi
