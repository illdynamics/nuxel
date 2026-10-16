#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/app-registry/app-registry.schema.json (service: None, risk: medium)
# staged source: configs/nuxel/app-registry/app-registry.schema.json
# previous-hash: da1dadb01e80db2afc4ff96033e88ec537e528ab4532bc6980c33a426f7fe787
set -eu
mkdir -p "$(dirname /etc/nuxel/app-registry/app-registry.schema.json)"
if [ -e /etc/nuxel/app-registry/app-registry.schema.json ]; then cp -a /etc/nuxel/app-registry/app-registry.schema.json /etc/nuxel/app-registry/app-registry.schema.json.nuxel-rollback; fi
test -f /etc/nuxel/app-registry/app-registry.schema.json.nuxel-staged
printf '%s  %s\n' da1dadb01e80db2afc4ff96033e88ec537e528ab4532bc6980c33a426f7fe787 /etc/nuxel/app-registry/app-registry.schema.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/app-registry/app-registry.schema.json.nuxel-staged /etc/nuxel/app-registry/app-registry.schema.json
sha256sum /etc/nuxel/app-registry/app-registry.schema.json | grep -q da1dadb01e80db2afc4ff96033e88ec537e528ab4532bc6980c33a426f7fe787
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/app-registry/app-registry.schema.json.nuxel-rollback ]; then cp -a /etc/nuxel/app-registry/app-registry.schema.json.nuxel-rollback /etc/nuxel/app-registry/app-registry.schema.json; true; fi
