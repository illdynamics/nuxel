#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-touch-arm.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-touch-arm.service
# previous-hash: 85f7f880f9f875059c0d160331f96f93a22d2a2f055a2ca5b3f9c2bba816ab29
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-touch-arm.service)"
if [ -e /etc/systemd/system/nuxel-touch-arm.service ]; then cp -a /etc/systemd/system/nuxel-touch-arm.service /etc/systemd/system/nuxel-touch-arm.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-touch-arm.service.nuxel-staged
printf '%s  %s\n' 85f7f880f9f875059c0d160331f96f93a22d2a2f055a2ca5b3f9c2bba816ab29 /etc/systemd/system/nuxel-touch-arm.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-touch-arm.service.nuxel-staged /etc/systemd/system/nuxel-touch-arm.service
sha256sum /etc/systemd/system/nuxel-touch-arm.service | grep -q 85f7f880f9f875059c0d160331f96f93a22d2a2f055a2ca5b3f9c2bba816ab29
systemctl daemon-reload
systemctl daemon-reload
systemctl is-active nuxel-wayland
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-touch-arm.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-touch-arm.service.nuxel-rollback /etc/systemd/system/nuxel-touch-arm.service; true; fi
