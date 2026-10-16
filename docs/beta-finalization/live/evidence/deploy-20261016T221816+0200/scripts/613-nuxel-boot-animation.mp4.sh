#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/share/nuxel/boot/nuxel-boot-animation.mp4 (service: nuxel-wayland, risk: high)
# staged source: assets/nuxel-boot-animation.mp4
# previous-hash: 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
set -eu
mkdir -p "$(dirname /usr/share/nuxel/boot/nuxel-boot-animation.mp4)"
if [ -e /usr/share/nuxel/boot/nuxel-boot-animation.mp4 ]; then cp -a /usr/share/nuxel/boot/nuxel-boot-animation.mp4 /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-rollback; fi
test -f /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-staged
printf '%s  %s\n' 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-staged /usr/share/nuxel/boot/nuxel-boot-animation.mp4
sha256sum /usr/share/nuxel/boot/nuxel-boot-animation.mp4 | grep -q 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb && test -s /usr/share/nuxel/boot/nuxel-boot-animation.mp4 && test -x /usr/lib/nuxel/nuxel-animation-claim
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-rollback ]; then cp -a /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-rollback /usr/share/nuxel/boot/nuxel-boot-animation.mp4; systemctl restart nuxel-wayland; fi
