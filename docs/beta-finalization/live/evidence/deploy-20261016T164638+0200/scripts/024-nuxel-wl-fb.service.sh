#!/bin/sh
# boot graph / session units -> /etc/systemd/system/nuxel-wl-fb.service (service: None, risk: high)
# staged source: services/nuxel-session/systemd/nuxel-wl-fb.service
# previous-hash: 75d7091c864913d3a7b1c9688d97b169239e37fef1aad3c844b9b263f1a48da4
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-wl-fb.service)"
if [ -e /etc/systemd/system/nuxel-wl-fb.service ]; then cp -a /etc/systemd/system/nuxel-wl-fb.service /etc/systemd/system/nuxel-wl-fb.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-wl-fb.service.nuxel-staged
printf '%s  %s\n' 75d7091c864913d3a7b1c9688d97b169239e37fef1aad3c844b9b263f1a48da4 /etc/systemd/system/nuxel-wl-fb.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-wl-fb.service.nuxel-staged /etc/systemd/system/nuxel-wl-fb.service
sha256sum /etc/systemd/system/nuxel-wl-fb.service | grep -q 75d7091c864913d3a7b1c9688d97b169239e37fef1aad3c844b9b263f1a48da4
systemctl is-active nuxel-wayland
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-wl-fb.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-wl-fb.service.nuxel-rollback /etc/systemd/system/nuxel-wl-fb.service; true; fi
