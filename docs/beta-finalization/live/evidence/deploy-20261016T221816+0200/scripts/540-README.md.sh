#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-console/README.md (service: None, risk: medium)
# staged source: services/nuxel-console/README.md
# previous-hash: b6b0fec2c3759ae3f5a80aafb41f61c5efb3351b856cdf3114e9a6450ed1b657
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-console/README.md)"
if [ -e /usr/lib/nuxel/nuxel-console/README.md ]; then cp -a /usr/lib/nuxel/nuxel-console/README.md /usr/lib/nuxel/nuxel-console/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-console/README.md.nuxel-staged
printf '%s  %s\n' b6b0fec2c3759ae3f5a80aafb41f61c5efb3351b856cdf3114e9a6450ed1b657 /usr/lib/nuxel/nuxel-console/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-console/README.md.nuxel-staged /usr/lib/nuxel/nuxel-console/README.md
sha256sum /usr/lib/nuxel/nuxel-console/README.md | grep -q b6b0fec2c3759ae3f5a80aafb41f61c5efb3351b856cdf3114e9a6450ed1b657
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-console/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-console/README.md.nuxel-rollback /usr/lib/nuxel/nuxel-console/README.md; true; fi
