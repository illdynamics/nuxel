#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/time/README.md (service: None, risk: medium)
# staged source: configs/nuxel/time/README.md
# previous-hash: 8de48671320ac022111cb112b80cc7ce7f752489e5274ad2e576864dcbbbc14c
set -eu
mkdir -p "$(dirname /etc/nuxel/time/README.md)"
if [ -e /etc/nuxel/time/README.md ]; then cp -a /etc/nuxel/time/README.md /etc/nuxel/time/README.md.nuxel-rollback; fi
test -f /etc/nuxel/time/README.md.nuxel-staged
printf '%s  %s\n' 8de48671320ac022111cb112b80cc7ce7f752489e5274ad2e576864dcbbbc14c /etc/nuxel/time/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/time/README.md.nuxel-staged /etc/nuxel/time/README.md
sha256sum /etc/nuxel/time/README.md | grep -q 8de48671320ac022111cb112b80cc7ce7f752489e5274ad2e576864dcbbbc14c
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/time/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/time/README.md.nuxel-rollback /etc/nuxel/time/README.md; true; fi
