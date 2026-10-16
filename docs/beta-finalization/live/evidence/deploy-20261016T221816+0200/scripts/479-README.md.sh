#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/sensors/README.md (service: None, risk: medium)
# staged source: configs/nuxel/sensors/README.md
# previous-hash: 40aca4b6bd6c078a77927ffe7a8bdb3ade19266033ce3972435e68f4666ddebb
set -eu
mkdir -p "$(dirname /etc/nuxel/sensors/README.md)"
if [ -e /etc/nuxel/sensors/README.md ]; then cp -a /etc/nuxel/sensors/README.md /etc/nuxel/sensors/README.md.nuxel-rollback; fi
test -f /etc/nuxel/sensors/README.md.nuxel-staged
printf '%s  %s\n' 40aca4b6bd6c078a77927ffe7a8bdb3ade19266033ce3972435e68f4666ddebb /etc/nuxel/sensors/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sensors/README.md.nuxel-staged /etc/nuxel/sensors/README.md
sha256sum /etc/nuxel/sensors/README.md | grep -q 40aca4b6bd6c078a77927ffe7a8bdb3ade19266033ce3972435e68f4666ddebb
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sensors/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/sensors/README.md.nuxel-rollback /etc/nuxel/sensors/README.md; true; fi
