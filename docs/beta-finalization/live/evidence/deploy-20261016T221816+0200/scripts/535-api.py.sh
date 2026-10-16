#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-bridge/api.py (service: None, risk: medium)
# staged source: services/nuxel-bridge/src/api.py
# previous-hash: cbbca5ae8d48fb3b0bbce842606a287b31e0f481fbbfe21bcc8bf9351e987614
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/api.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged
printf '%s  %s\n' cbbca5ae8d48fb3b0bbce842606a287b31e0f481fbbfe21bcc8bf9351e987614 /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/api.py
sha256sum /usr/lib/nuxel/nuxel-bridge/api.py | grep -q cbbca5ae8d48fb3b0bbce842606a287b31e0f481fbbfe21bcc8bf9351e987614
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/api.py.nuxel-rollback /usr/lib/nuxel/nuxel-bridge/api.py; true; fi
