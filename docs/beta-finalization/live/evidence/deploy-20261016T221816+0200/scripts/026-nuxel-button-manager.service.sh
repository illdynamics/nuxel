#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-button-manager.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-button-manager.service
# previous-hash: c0bc10c448a500efc5fc4edff6d308ae69d583bffc6da6c90604371547b3c1a9
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-button-manager.service)"
if [ -e /etc/systemd/system/nuxel-button-manager.service ]; then cp -a /etc/systemd/system/nuxel-button-manager.service /etc/systemd/system/nuxel-button-manager.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-button-manager.service.nuxel-staged
printf '%s  %s\n' c0bc10c448a500efc5fc4edff6d308ae69d583bffc6da6c90604371547b3c1a9 /etc/systemd/system/nuxel-button-manager.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-button-manager.service.nuxel-staged /etc/systemd/system/nuxel-button-manager.service
sha256sum /etc/systemd/system/nuxel-button-manager.service | grep -q c0bc10c448a500efc5fc4edff6d308ae69d583bffc6da6c90604371547b3c1a9
systemctl daemon-reload
systemctl daemon-reload
systemctl is-active nuxel-wayland
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-button-manager.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-button-manager.service.nuxel-rollback /etc/systemd/system/nuxel-button-manager.service; true; fi
