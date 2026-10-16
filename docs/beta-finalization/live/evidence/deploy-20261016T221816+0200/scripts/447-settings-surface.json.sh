#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/buttons/settings-surface.json (service: None, risk: medium)
# staged source: configs/nuxel/buttons/settings-surface.json
# previous-hash: 4c9533d8efd8faabfc991d69d9e21066fedc21a7483caec3fce48659c29f7e4c
set -eu
mkdir -p "$(dirname /etc/nuxel/buttons/settings-surface.json)"
if [ -e /etc/nuxel/buttons/settings-surface.json ]; then cp -a /etc/nuxel/buttons/settings-surface.json /etc/nuxel/buttons/settings-surface.json.nuxel-rollback; fi
test -f /etc/nuxel/buttons/settings-surface.json.nuxel-staged
printf '%s  %s\n' 4c9533d8efd8faabfc991d69d9e21066fedc21a7483caec3fce48659c29f7e4c /etc/nuxel/buttons/settings-surface.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/buttons/settings-surface.json.nuxel-staged /etc/nuxel/buttons/settings-surface.json
sha256sum /etc/nuxel/buttons/settings-surface.json | grep -q 4c9533d8efd8faabfc991d69d9e21066fedc21a7483caec3fce48659c29f7e4c
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/buttons/settings-surface.json.nuxel-rollback ]; then cp -a /etc/nuxel/buttons/settings-surface.json.nuxel-rollback /etc/nuxel/buttons/settings-surface.json; true; fi
