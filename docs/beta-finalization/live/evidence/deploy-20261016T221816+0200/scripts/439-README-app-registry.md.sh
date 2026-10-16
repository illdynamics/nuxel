#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/app-registry/README-app-registry.md (service: None, risk: medium)
# staged source: configs/nuxel/app-registry/README-app-registry.md
# previous-hash: cb3bf374db96bd182b37bc7dfeffad26508cb8fe648df5101ed5c431707a0fcd
set -eu
mkdir -p "$(dirname /etc/nuxel/app-registry/README-app-registry.md)"
if [ -e /etc/nuxel/app-registry/README-app-registry.md ]; then cp -a /etc/nuxel/app-registry/README-app-registry.md /etc/nuxel/app-registry/README-app-registry.md.nuxel-rollback; fi
test -f /etc/nuxel/app-registry/README-app-registry.md.nuxel-staged
printf '%s  %s\n' cb3bf374db96bd182b37bc7dfeffad26508cb8fe648df5101ed5c431707a0fcd /etc/nuxel/app-registry/README-app-registry.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/app-registry/README-app-registry.md.nuxel-staged /etc/nuxel/app-registry/README-app-registry.md
sha256sum /etc/nuxel/app-registry/README-app-registry.md | grep -q cb3bf374db96bd182b37bc7dfeffad26508cb8fe648df5101ed5c431707a0fcd
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/app-registry/README-app-registry.md.nuxel-rollback ]; then cp -a /etc/nuxel/app-registry/README-app-registry.md.nuxel-rollback /etc/nuxel/app-registry/README-app-registry.md; true; fi
