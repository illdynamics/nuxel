#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-notifications/README.md (service: None, risk: medium)
# staged source: services/nuxel-notifications/README.md
# previous-hash: b0bdc5a098e542ed25656d0b92e3d2ed8ef3b6c0b2c67964f47c0f234617098b
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-notifications/README.md)"
if [ -e /usr/lib/nuxel/nuxel-notifications/README.md ]; then cp -a /usr/lib/nuxel/nuxel-notifications/README.md /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-staged
printf '%s  %s\n' b0bdc5a098e542ed25656d0b92e3d2ed8ef3b6c0b2c67964f47c0f234617098b /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-staged /usr/lib/nuxel/nuxel-notifications/README.md
sha256sum /usr/lib/nuxel/nuxel-notifications/README.md | grep -q b0bdc5a098e542ed25656d0b92e3d2ed8ef3b6c0b2c67964f47c0f234617098b
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-notifications/README.md.nuxel-rollback /usr/lib/nuxel/nuxel-notifications/README.md; true; fi
