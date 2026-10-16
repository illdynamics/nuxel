#!/bin/sh
# boot animation handoff -> /etc/nuxel/boot/verbose-boot.json (service: nuxel-wayland, risk: high)
# staged source: configs/nuxel/boot/verbose-boot.json
# previous-hash: 16a46b63e6ea82bdaa9528ac1dd553852642e164f02761892d85eeaa3a12f18e
set -eu
mkdir -p "$(dirname /etc/nuxel/boot/verbose-boot.json)"
if [ -e /etc/nuxel/boot/verbose-boot.json ]; then cp -a /etc/nuxel/boot/verbose-boot.json /etc/nuxel/boot/verbose-boot.json.nuxel-rollback; fi
test -f /etc/nuxel/boot/verbose-boot.json.nuxel-staged
printf '%s  %s\n' 16a46b63e6ea82bdaa9528ac1dd553852642e164f02761892d85eeaa3a12f18e /etc/nuxel/boot/verbose-boot.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/boot/verbose-boot.json.nuxel-staged /etc/nuxel/boot/verbose-boot.json
sha256sum /etc/nuxel/boot/verbose-boot.json | grep -q 16a46b63e6ea82bdaa9528ac1dd553852642e164f02761892d85eeaa3a12f18e
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
test -s /var/lib/nuxel/animation
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/boot/verbose-boot.json.nuxel-rollback ]; then cp -a /etc/nuxel/boot/verbose-boot.json.nuxel-rollback /etc/nuxel/boot/verbose-boot.json; systemctl restart nuxel-wayland; fi
