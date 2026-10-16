#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/manifest.json
# previous-hash: 0006c9b7bb14109736e05a5a3e0a64d5cf96fb8fd5a4f906b770e2ca5c864b7e
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/manifest.json)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/manifest.json ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/manifest.json /home/nuxel/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged
printf '%s  %s\n' 0006c9b7bb14109736e05a5a3e0a64d5cf96fb8fd5a4f906b770e2ca5c864b7e /home/nuxel/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/manifest.json
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/manifest.json | grep -q 0006c9b7bb14109736e05a5a3e0a64d5cf96fb8fd5a4f906b770e2ca5c864b7e
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/manifest.json; systemctl restart nuxel-web; fi
