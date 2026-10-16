#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/security/README.md (service: None, risk: medium)
# staged source: configs/nuxel/security/README.md
# previous-hash: a3c64f1e57aae64790ca06e444c86ba4c570f6fb8819deb9006d4f1c52e98546
set -eu
mkdir -p "$(dirname /etc/nuxel/security/README.md)"
if [ -e /etc/nuxel/security/README.md ]; then cp -a /etc/nuxel/security/README.md /etc/nuxel/security/README.md.nuxel-rollback; fi
test -f /etc/nuxel/security/README.md.nuxel-staged
printf '%s  %s\n' a3c64f1e57aae64790ca06e444c86ba4c570f6fb8819deb9006d4f1c52e98546 /etc/nuxel/security/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/security/README.md.nuxel-staged /etc/nuxel/security/README.md
sha256sum /etc/nuxel/security/README.md | grep -q a3c64f1e57aae64790ca06e444c86ba4c570f6fb8819deb9006d4f1c52e98546
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/security/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/security/README.md.nuxel-rollback /etc/nuxel/security/README.md; true; fi
