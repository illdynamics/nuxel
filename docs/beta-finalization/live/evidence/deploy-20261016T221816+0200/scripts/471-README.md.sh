#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/power/README.md (service: None, risk: medium)
# staged source: configs/nuxel/power/README.md
# previous-hash: 459bf3b3d641fa66b7b064a23fd0b0775d23dbf9a582f030f7792fde2ba9ed98
set -eu
mkdir -p "$(dirname /etc/nuxel/power/README.md)"
if [ -e /etc/nuxel/power/README.md ]; then cp -a /etc/nuxel/power/README.md /etc/nuxel/power/README.md.nuxel-rollback; fi
test -f /etc/nuxel/power/README.md.nuxel-staged
printf '%s  %s\n' 459bf3b3d641fa66b7b064a23fd0b0775d23dbf9a582f030f7792fde2ba9ed98 /etc/nuxel/power/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/power/README.md.nuxel-staged /etc/nuxel/power/README.md
sha256sum /etc/nuxel/power/README.md | grep -q 459bf3b3d641fa66b7b064a23fd0b0775d23dbf9a582f030f7792fde2ba9ed98
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/power/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/power/README.md.nuxel-rollback /etc/nuxel/power/README.md; true; fi
