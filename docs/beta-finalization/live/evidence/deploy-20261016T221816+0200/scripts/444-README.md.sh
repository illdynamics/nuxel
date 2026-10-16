#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/bootmode/README.md (service: None, risk: medium)
# staged source: configs/nuxel/bootmode/README.md
# previous-hash: 3cbae6e1601c7d29e7872c1cf6801f4efcc0366b0528ce35f546813594365d32
set -eu
mkdir -p "$(dirname /etc/nuxel/bootmode/README.md)"
if [ -e /etc/nuxel/bootmode/README.md ]; then cp -a /etc/nuxel/bootmode/README.md /etc/nuxel/bootmode/README.md.nuxel-rollback; fi
test -f /etc/nuxel/bootmode/README.md.nuxel-staged
printf '%s  %s\n' 3cbae6e1601c7d29e7872c1cf6801f4efcc0366b0528ce35f546813594365d32 /etc/nuxel/bootmode/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bootmode/README.md.nuxel-staged /etc/nuxel/bootmode/README.md
sha256sum /etc/nuxel/bootmode/README.md | grep -q 3cbae6e1601c7d29e7872c1cf6801f4efcc0366b0528ce35f546813594365d32
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/bootmode/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/bootmode/README.md.nuxel-rollback /etc/nuxel/bootmode/README.md; true; fi
