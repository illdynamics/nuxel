#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/gnss/README.md (service: None, risk: medium)
# staged source: configs/nuxel/gnss/README.md
# previous-hash: dd26f110c8449196c1320a7ee4e02ea92ba010c621302125a9105b728c63cdeb
set -eu
mkdir -p "$(dirname /etc/nuxel/gnss/README.md)"
if [ -e /etc/nuxel/gnss/README.md ]; then cp -a /etc/nuxel/gnss/README.md /etc/nuxel/gnss/README.md.nuxel-rollback; fi
test -f /etc/nuxel/gnss/README.md.nuxel-staged
printf '%s  %s\n' dd26f110c8449196c1320a7ee4e02ea92ba010c621302125a9105b728c63cdeb /etc/nuxel/gnss/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/gnss/README.md.nuxel-staged /etc/nuxel/gnss/README.md
sha256sum /etc/nuxel/gnss/README.md | grep -q dd26f110c8449196c1320a7ee4e02ea92ba010c621302125a9105b728c63cdeb
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/gnss/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/README.md.nuxel-rollback /etc/nuxel/gnss/README.md; true; fi
