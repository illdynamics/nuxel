#!/bin/sh
# boot-animation userspace runtime + asset placement -> /usr/share/nuxel/boot/nuxel-boot-animation.mp4 (service: nuxel-wayland, risk: high)
# staged source: assets/nuxel-boot-animation.mp4
# previous-hash: 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-rollback ]; then cp -a /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-rollback /usr/share/nuxel/boot/nuxel-boot-animation.mp4; systemctl restart nuxel-wayland; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
if [ -e /usr/share/nuxel/boot/nuxel-boot-animation.mp4 ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/boot/nuxel-boot-animation.mp4 | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/boot/nuxel-boot-animation.mp4)"
if [ -e /usr/share/nuxel/boot/nuxel-boot-animation.mp4 ] && [ ! -e /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-rollback ]; then cp -a /usr/share/nuxel/boot/nuxel-boot-animation.mp4 /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-rollback; fi
test -f /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-staged
printf '%s  %s\n' 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/boot/nuxel-boot-animation.mp4.nuxel-staged /usr/share/nuxel/boot/nuxel-boot-animation.mp4
sha256sum /usr/share/nuxel/boot/nuxel-boot-animation.mp4 | grep -q 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
systemctl restart nuxel-wayland
systemctl is-active nuxel-wayland
/usr/local/bin/nuxel-fb-owner-assert.sh --expect nuxel-wl-fb
echo INSTALL-OK
