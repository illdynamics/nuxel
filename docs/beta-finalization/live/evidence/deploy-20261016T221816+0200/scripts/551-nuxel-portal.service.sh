#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-portal.service (service: None, risk: medium)
# staged source: services/nuxel-portal/systemd/nuxel-portal.service
# previous-hash: b86401526672305ab3b5cc3a5a05c3528d47d4fc584f3dd5088a062962893832
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-portal.service)"
if [ -e /etc/systemd/system/nuxel-portal.service ]; then cp -a /etc/systemd/system/nuxel-portal.service /etc/systemd/system/nuxel-portal.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-portal.service.nuxel-staged
printf '%s  %s\n' b86401526672305ab3b5cc3a5a05c3528d47d4fc584f3dd5088a062962893832 /etc/systemd/system/nuxel-portal.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-portal.service.nuxel-staged /etc/systemd/system/nuxel-portal.service
sha256sum /etc/systemd/system/nuxel-portal.service | grep -q b86401526672305ab3b5cc3a5a05c3528d47d4fc584f3dd5088a062962893832
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-portal.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-portal.service.nuxel-rollback /etc/systemd/system/nuxel-portal.service; true; fi
