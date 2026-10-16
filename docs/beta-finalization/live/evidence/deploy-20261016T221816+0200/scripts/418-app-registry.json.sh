#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-common/app-registry.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/app-registry.json
# previous-hash: c1fb6b5ba535b34c0b3f9db80b6130e356ba2d8d6efd4791f57444d03c054b58
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/app-registry.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged
printf '%s  %s\n' c1fb6b5ba535b34c0b3f9db80b6130e356ba2d8d6efd4791f57444d03c054b58 /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/app-registry.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/app-registry.json | grep -q c1fb6b5ba535b34c0b3f9db80b6130e356ba2d8d6efd4791f57444d03c054b58
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/bridge.js)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-common/app-registry.json; systemctl restart nuxel-web; fi
