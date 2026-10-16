#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-bridge (service: None, risk: medium)
# staged source: services/nuxel-bridge/bin/nuxel-bridge
# previous-hash: 004847ca71df3ad46007206b9f85128a1d4787a547bdbd8c793df66b61e65e01
set -eu
mkdir -p "$(dirname /usr/bin/nuxel-bridge)"
if [ -e /usr/bin/nuxel-bridge ]; then cp -a /usr/bin/nuxel-bridge /usr/bin/nuxel-bridge.nuxel-rollback; fi
test -f /usr/bin/nuxel-bridge.nuxel-staged
printf '%s  %s\n' 004847ca71df3ad46007206b9f85128a1d4787a547bdbd8c793df66b61e65e01 /usr/bin/nuxel-bridge.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-bridge.nuxel-staged /usr/bin/nuxel-bridge
sha256sum /usr/bin/nuxel-bridge | grep -q 004847ca71df3ad46007206b9f85128a1d4787a547bdbd8c793df66b61e65e01
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/bin/nuxel-bridge.nuxel-rollback ]; then cp -a /usr/bin/nuxel-bridge.nuxel-rollback /usr/bin/nuxel-bridge; true; fi
