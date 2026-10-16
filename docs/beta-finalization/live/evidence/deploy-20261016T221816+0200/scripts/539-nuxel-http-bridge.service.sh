#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-http-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-http-bridge.service
# previous-hash: 3d78284e5e46e6e7d5c73ef21f2256dde4a6ddf38c365b61be02f2d455934702
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-http-bridge.service)"
if [ -e /etc/systemd/system/nuxel-http-bridge.service ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged
printf '%s  %s\n' 3d78284e5e46e6e7d5c73ef21f2256dde4a6ddf38c365b61be02f2d455934702 /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged /etc/systemd/system/nuxel-http-bridge.service
sha256sum /etc/systemd/system/nuxel-http-bridge.service | grep -q 3d78284e5e46e6e7d5c73ef21f2256dde4a6ddf38c365b61be02f2d455934702
systemctl daemon-reload
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
test -x /usr/bin/nuxel-bridge && test -x /usr/bin/nuxel-http-bridge && test -x /usr/bin/nuxel-portal && test -x /usr/bin/nuxel-notifications && test -s /usr/lib/nuxel/nuxel-web-server.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback /etc/systemd/system/nuxel-http-bridge.service; true; fi
