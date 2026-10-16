#!/bin/sh
# app registry consumers/entries + verifiers -> /etc/nuxel/app-registry/app_registry.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/app-registry.json
# previous-hash: c1fb6b5ba535b34c0b3f9db80b6130e356ba2d8d6efd4791f57444d03c054b58
set -eu
mkdir -p "$(dirname /etc/nuxel/app-registry/app_registry.json)"
if [ -e /etc/nuxel/app-registry/app_registry.json ]; then cp -a /etc/nuxel/app-registry/app_registry.json /etc/nuxel/app-registry/app_registry.json.nuxel-rollback; fi
test -f /etc/nuxel/app-registry/app_registry.json.nuxel-staged
printf '%s  %s\n' c1fb6b5ba535b34c0b3f9db80b6130e356ba2d8d6efd4791f57444d03c054b58 /etc/nuxel/app-registry/app_registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/app-registry/app_registry.json.nuxel-staged /etc/nuxel/app-registry/app_registry.json
sha256sum /etc/nuxel/app-registry/app_registry.json | grep -q c1fb6b5ba535b34c0b3f9db80b6130e356ba2d8d6efd4791f57444d03c054b58
systemctl restart nuxel-web
systemctl is-active nuxel-web
python3 -c "import json;a=json.load(open('/etc/nuxel/app-registry/app_registry.json'));assert a['registry_version']>=4" && test -x /usr/local/bin/verify-app-registry.py
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/app-registry/app_registry.json.nuxel-rollback ]; then cp -a /etc/nuxel/app-registry/app_registry.json.nuxel-rollback /etc/nuxel/app-registry/app_registry.json; systemctl restart nuxel-web; fi
