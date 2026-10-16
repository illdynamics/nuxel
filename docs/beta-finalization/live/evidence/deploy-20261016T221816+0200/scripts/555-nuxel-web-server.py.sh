#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-web-server.py (service: None, risk: medium)
# staged source: services/nuxel-web/bin/nuxel-web-server.py
# previous-hash: b17fb3e700ed3918691a395895090ca68eab5fe45b1f9a01a63a270f27072520
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-web-server.py)"
if [ -e /usr/lib/nuxel/nuxel-web-server.py ]; then cp -a /usr/lib/nuxel/nuxel-web-server.py /usr/lib/nuxel/nuxel-web-server.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-web-server.py.nuxel-staged
printf '%s  %s\n' b17fb3e700ed3918691a395895090ca68eab5fe45b1f9a01a63a270f27072520 /usr/lib/nuxel/nuxel-web-server.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-web-server.py.nuxel-staged /usr/lib/nuxel/nuxel-web-server.py
sha256sum /usr/lib/nuxel/nuxel-web-server.py | grep -q b17fb3e700ed3918691a395895090ca68eab5fe45b1f9a01a63a270f27072520
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-web-server.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-web-server.py.nuxel-rollback /usr/lib/nuxel/nuxel-web-server.py; true; fi
