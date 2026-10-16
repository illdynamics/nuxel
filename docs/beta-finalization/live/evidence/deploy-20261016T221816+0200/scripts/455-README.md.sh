#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/haptics/README.md (service: None, risk: medium)
# staged source: configs/nuxel/haptics/README.md
# previous-hash: 12560ef110c7503b43a8741c7cc282a76bc45ec64c540ff982992958e5c077b7
set -eu
mkdir -p "$(dirname /etc/nuxel/haptics/README.md)"
if [ -e /etc/nuxel/haptics/README.md ]; then cp -a /etc/nuxel/haptics/README.md /etc/nuxel/haptics/README.md.nuxel-rollback; fi
test -f /etc/nuxel/haptics/README.md.nuxel-staged
printf '%s  %s\n' 12560ef110c7503b43a8741c7cc282a76bc45ec64c540ff982992958e5c077b7 /etc/nuxel/haptics/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/haptics/README.md.nuxel-staged /etc/nuxel/haptics/README.md
sha256sum /etc/nuxel/haptics/README.md | grep -q 12560ef110c7503b43a8741c7cc282a76bc45ec64c540ff982992958e5c077b7
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/haptics/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/README.md.nuxel-rollback /etc/nuxel/haptics/README.md; true; fi
