#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/gnss/gnss.json (service: None, risk: medium)
# staged source: configs/nuxel/gnss/gnss.json
# previous-hash: efe9921cfe300e79c86fb444681354e02707fd3242b09f319e38bc79f9e5efb0
set -eu
mkdir -p "$(dirname /etc/nuxel/gnss/gnss.json)"
if [ -e /etc/nuxel/gnss/gnss.json ]; then cp -a /etc/nuxel/gnss/gnss.json /etc/nuxel/gnss/gnss.json.nuxel-rollback; fi
test -f /etc/nuxel/gnss/gnss.json.nuxel-staged
printf '%s  %s\n' efe9921cfe300e79c86fb444681354e02707fd3242b09f319e38bc79f9e5efb0 /etc/nuxel/gnss/gnss.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/gnss/gnss.json.nuxel-staged /etc/nuxel/gnss/gnss.json
sha256sum /etc/nuxel/gnss/gnss.json | grep -q efe9921cfe300e79c86fb444681354e02707fd3242b09f319e38bc79f9e5efb0
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/gnss/gnss.json.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/gnss.json.nuxel-rollback /etc/nuxel/gnss/gnss.json; true; fi
