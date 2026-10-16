#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-http-bridge (service: None, risk: medium)
# staged source: services/nuxel-bridge/bin/nuxel-http-bridge
# previous-hash: e16c4faff5540d1b3667b7a158983b86ca0d9bd03822689f3fd084fa7236a50f
set -eu
mkdir -p "$(dirname /usr/bin/nuxel-http-bridge)"
if [ -e /usr/bin/nuxel-http-bridge ]; then cp -a /usr/bin/nuxel-http-bridge /usr/bin/nuxel-http-bridge.nuxel-rollback; fi
test -f /usr/bin/nuxel-http-bridge.nuxel-staged
printf '%s  %s\n' e16c4faff5540d1b3667b7a158983b86ca0d9bd03822689f3fd084fa7236a50f /usr/bin/nuxel-http-bridge.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-http-bridge.nuxel-staged /usr/bin/nuxel-http-bridge
sha256sum /usr/bin/nuxel-http-bridge | grep -q e16c4faff5540d1b3667b7a158983b86ca0d9bd03822689f3fd084fa7236a50f
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/bin/nuxel-http-bridge.nuxel-rollback ]; then cp -a /usr/bin/nuxel-http-bridge.nuxel-rollback /usr/bin/nuxel-http-bridge; true; fi
