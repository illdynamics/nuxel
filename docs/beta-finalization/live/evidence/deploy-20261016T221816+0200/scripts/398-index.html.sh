#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/terminal/index.html
# previous-hash: 0a7ebaa79edf66f659b58e2f9d3f49cb77a5cd255f3a22132b399b244b05f2ff
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html.nuxel-staged
printf '%s  %s\n' 0a7ebaa79edf66f659b58e2f9d3f49cb77a5cd255f3a22132b399b244b05f2ff /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html | grep -q 0a7ebaa79edf66f659b58e2f9d3f49cb77a5cd255f3a22132b399b244b05f2ff
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/terminal/index.html; systemctl restart nuxel-web; fi
