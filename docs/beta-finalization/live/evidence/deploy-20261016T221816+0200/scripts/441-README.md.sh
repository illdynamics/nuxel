#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/bluetooth/README.md (service: None, risk: medium)
# staged source: configs/nuxel/bluetooth/README.md
# previous-hash: 0fd0a10c0a58154e242db2ddc61c9671e8a8cf64a055ebf3d226b4370ebabbba
set -eu
mkdir -p "$(dirname /etc/nuxel/bluetooth/README.md)"
if [ -e /etc/nuxel/bluetooth/README.md ]; then cp -a /etc/nuxel/bluetooth/README.md /etc/nuxel/bluetooth/README.md.nuxel-rollback; fi
test -f /etc/nuxel/bluetooth/README.md.nuxel-staged
printf '%s  %s\n' 0fd0a10c0a58154e242db2ddc61c9671e8a8cf64a055ebf3d226b4370ebabbba /etc/nuxel/bluetooth/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bluetooth/README.md.nuxel-staged /etc/nuxel/bluetooth/README.md
sha256sum /etc/nuxel/bluetooth/README.md | grep -q 0fd0a10c0a58154e242db2ddc61c9671e8a8cf64a055ebf3d226b4370ebabbba
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/bluetooth/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/bluetooth/README.md.nuxel-rollback /etc/nuxel/bluetooth/README.md; true; fi
