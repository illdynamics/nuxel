#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-fallback.service (service: None, risk: medium)
# staged source: services/nuxel-session/systemd/nuxel-fallback.service
# previous-hash: cbc1c5d18b365c7ecf7d544a7eb4932171cfef468429c3813df196adaca11233
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-fallback.service)"
if [ -e /etc/systemd/system/nuxel-fallback.service ]; then cp -a /etc/systemd/system/nuxel-fallback.service /etc/systemd/system/nuxel-fallback.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-fallback.service.nuxel-staged
printf '%s  %s\n' cbc1c5d18b365c7ecf7d544a7eb4932171cfef468429c3813df196adaca11233 /etc/systemd/system/nuxel-fallback.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-fallback.service.nuxel-staged /etc/systemd/system/nuxel-fallback.service
sha256sum /etc/systemd/system/nuxel-fallback.service | grep -q cbc1c5d18b365c7ecf7d544a7eb4932171cfef468429c3813df196adaca11233
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-fallback.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-fallback.service.nuxel-rollback /etc/systemd/system/nuxel-fallback.service; true; fi
