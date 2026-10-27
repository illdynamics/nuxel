#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/nuxel-boot-animation.mp4
# previous-hash: 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-staged
printf '%s  %s\n' 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-boot-animation.mp4 | grep -q 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
echo INSTALL-OK
