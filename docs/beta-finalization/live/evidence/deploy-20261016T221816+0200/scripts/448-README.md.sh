#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/camera/README.md (service: None, risk: medium)
# staged source: configs/nuxel/camera/README.md
# previous-hash: 5294d8669862802992cade97eab909be75ab53d811460ecbfb8f263b4f9d1213
set -eu
mkdir -p "$(dirname /etc/nuxel/camera/README.md)"
if [ -e /etc/nuxel/camera/README.md ]; then cp -a /etc/nuxel/camera/README.md /etc/nuxel/camera/README.md.nuxel-rollback; fi
test -f /etc/nuxel/camera/README.md.nuxel-staged
printf '%s  %s\n' 5294d8669862802992cade97eab909be75ab53d811460ecbfb8f263b4f9d1213 /etc/nuxel/camera/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/camera/README.md.nuxel-staged /etc/nuxel/camera/README.md
sha256sum /etc/nuxel/camera/README.md | grep -q 5294d8669862802992cade97eab909be75ab53d811460ecbfb8f263b4f9d1213
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/camera/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/camera/README.md.nuxel-rollback /etc/nuxel/camera/README.md; true; fi
