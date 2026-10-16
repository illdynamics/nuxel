#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4 (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4
# previous-hash: 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4 ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4 | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4 ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4 /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4.nuxel-staged
printf '%s  %s\n' 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/assets/nuxel-boot-animation.mp4 | grep -q 280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
