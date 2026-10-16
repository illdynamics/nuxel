#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/bin/nuxel-portal (service: None, risk: medium)
# staged source: services/nuxel-portal/bin/nuxel-portal
# previous-hash: c08a58e33ef744356112ba6c25c070d454201bd72e338b6168327f92bcfc7815
set -eu
mkdir -p "$(dirname /usr/bin/nuxel-portal)"
if [ -e /usr/bin/nuxel-portal ]; then cp -a /usr/bin/nuxel-portal /usr/bin/nuxel-portal.nuxel-rollback; fi
test -f /usr/bin/nuxel-portal.nuxel-staged
printf '%s  %s\n' c08a58e33ef744356112ba6c25c070d454201bd72e338b6168327f92bcfc7815 /usr/bin/nuxel-portal.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/bin/nuxel-portal.nuxel-staged /usr/bin/nuxel-portal
sha256sum /usr/bin/nuxel-portal | grep -q c08a58e33ef744356112ba6c25c070d454201bd72e338b6168327f92bcfc7815
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/bin/nuxel-portal.nuxel-rollback ]; then cp -a /usr/bin/nuxel-portal.nuxel-rollback /usr/bin/nuxel-portal; true; fi
