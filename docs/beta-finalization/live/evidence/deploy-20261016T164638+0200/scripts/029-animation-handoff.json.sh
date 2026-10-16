#!/bin/sh
# boot animation handoff -> /etc/nuxel/boot/animation-handoff.json (service: nuxel-wayland, risk: high)
# staged source: configs/nuxel/boot/animation-handoff.json
# previous-hash: 5deb569e5f1049fa2f5689ccb35cfab2758ad717ffd9d5ed9e9efceac856c00c
set -eu
mkdir -p "$(dirname /etc/nuxel/boot/animation-handoff.json)"
if [ -e /etc/nuxel/boot/animation-handoff.json ]; then cp -a /etc/nuxel/boot/animation-handoff.json /etc/nuxel/boot/animation-handoff.json.nuxel-rollback; fi
test -f /etc/nuxel/boot/animation-handoff.json.nuxel-staged
printf '%s  %s\n' 5deb569e5f1049fa2f5689ccb35cfab2758ad717ffd9d5ed9e9efceac856c00c /etc/nuxel/boot/animation-handoff.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/boot/animation-handoff.json.nuxel-staged /etc/nuxel/boot/animation-handoff.json
sha256sum /etc/nuxel/boot/animation-handoff.json | grep -q 5deb569e5f1049fa2f5689ccb35cfab2758ad717ffd9d5ed9e9efceac856c00c
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
test -s /var/lib/nuxel/animation
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/boot/animation-handoff.json.nuxel-rollback ]; then cp -a /etc/nuxel/boot/animation-handoff.json.nuxel-rollback /etc/nuxel/boot/animation-handoff.json; systemctl restart nuxel-wayland; fi
