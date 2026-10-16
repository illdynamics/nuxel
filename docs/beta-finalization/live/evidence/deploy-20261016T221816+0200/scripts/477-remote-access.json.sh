#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/security/remote-access.json (service: None, risk: medium)
# staged source: configs/nuxel/security/remote-access.json
# previous-hash: baf17e455be7206b665cbbb2574971244b8366122552a6e5e9c35f0fba619c60
set -eu
mkdir -p "$(dirname /etc/nuxel/security/remote-access.json)"
if [ -e /etc/nuxel/security/remote-access.json ]; then cp -a /etc/nuxel/security/remote-access.json /etc/nuxel/security/remote-access.json.nuxel-rollback; fi
test -f /etc/nuxel/security/remote-access.json.nuxel-staged
printf '%s  %s\n' baf17e455be7206b665cbbb2574971244b8366122552a6e5e9c35f0fba619c60 /etc/nuxel/security/remote-access.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/security/remote-access.json.nuxel-staged /etc/nuxel/security/remote-access.json
sha256sum /etc/nuxel/security/remote-access.json | grep -q baf17e455be7206b665cbbb2574971244b8366122552a6e5e9c35f0fba619c60
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/security/remote-access.json.nuxel-rollback ]; then cp -a /etc/nuxel/security/remote-access.json.nuxel-rollback /etc/nuxel/security/remote-access.json; true; fi
