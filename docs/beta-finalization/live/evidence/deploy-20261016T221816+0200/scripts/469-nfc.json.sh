#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/nfc/nfc.json (service: None, risk: medium)
# staged source: configs/nuxel/nfc/nfc.json
# previous-hash: 1f84eaf6dc911c538d9f73df54989bae2ce20c7126ae07ba9f4a9b6e89172757
set -eu
mkdir -p "$(dirname /etc/nuxel/nfc/nfc.json)"
if [ -e /etc/nuxel/nfc/nfc.json ]; then cp -a /etc/nuxel/nfc/nfc.json /etc/nuxel/nfc/nfc.json.nuxel-rollback; fi
test -f /etc/nuxel/nfc/nfc.json.nuxel-staged
printf '%s  %s\n' 1f84eaf6dc911c538d9f73df54989bae2ce20c7126ae07ba9f4a9b6e89172757 /etc/nuxel/nfc/nfc.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/nfc/nfc.json.nuxel-staged /etc/nuxel/nfc/nfc.json
sha256sum /etc/nuxel/nfc/nfc.json | grep -q 1f84eaf6dc911c538d9f73df54989bae2ce20c7126ae07ba9f4a9b6e89172757
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/nfc/nfc.json.nuxel-rollback ]; then cp -a /etc/nuxel/nfc/nfc.json.nuxel-rollback /etc/nuxel/nfc/nfc.json; true; fi
