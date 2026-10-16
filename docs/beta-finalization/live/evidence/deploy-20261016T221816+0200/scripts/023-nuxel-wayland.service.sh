#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-wayland.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-wayland.service
# previous-hash: 634140ec38b7613294564b7b879654002e3046bd98ac9f0a6e9983a5a8385a00
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-wayland.service)"
if [ -e /etc/systemd/system/nuxel-wayland.service ]; then cp -a /etc/systemd/system/nuxel-wayland.service /etc/systemd/system/nuxel-wayland.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-wayland.service.nuxel-staged
printf '%s  %s\n' 634140ec38b7613294564b7b879654002e3046bd98ac9f0a6e9983a5a8385a00 /etc/systemd/system/nuxel-wayland.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-wayland.service.nuxel-staged /etc/systemd/system/nuxel-wayland.service
sha256sum /etc/systemd/system/nuxel-wayland.service | grep -q 634140ec38b7613294564b7b879654002e3046bd98ac9f0a6e9983a5a8385a00
systemctl daemon-reload
systemctl daemon-reload
systemctl is-active nuxel-wayland
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-wayland.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-wayland.service.nuxel-rollback /etc/systemd/system/nuxel-wayland.service; true; fi
