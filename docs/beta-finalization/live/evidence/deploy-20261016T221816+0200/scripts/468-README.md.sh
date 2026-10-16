#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/nfc/README.md (service: None, risk: medium)
# staged source: configs/nuxel/nfc/README.md
# previous-hash: 8f5e409c7b4ffca5a7b88a397c257da4a71fff9d42f08502ea2d94ca213f7801
set -eu
mkdir -p "$(dirname /etc/nuxel/nfc/README.md)"
if [ -e /etc/nuxel/nfc/README.md ]; then cp -a /etc/nuxel/nfc/README.md /etc/nuxel/nfc/README.md.nuxel-rollback; fi
test -f /etc/nuxel/nfc/README.md.nuxel-staged
printf '%s  %s\n' 8f5e409c7b4ffca5a7b88a397c257da4a71fff9d42f08502ea2d94ca213f7801 /etc/nuxel/nfc/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/nfc/README.md.nuxel-staged /etc/nuxel/nfc/README.md
sha256sum /etc/nuxel/nfc/README.md | grep -q 8f5e409c7b4ffca5a7b88a397c257da4a71fff9d42f08502ea2d94ca213f7801
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/nfc/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/nfc/README.md.nuxel-rollback /etc/nuxel/nfc/README.md; true; fi
