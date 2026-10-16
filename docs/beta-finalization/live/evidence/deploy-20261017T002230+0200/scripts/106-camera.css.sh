#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/css/camera.css
# previous-hash: 08b27fb3571128382da7bf4cf9d14e213db716789938df8fe0d11668ccb4c73a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css.nuxel-staged
printf '%s  %s\n' 08b27fb3571128382da7bf4cf9d14e213db716789938df8fe0d11668ccb4c73a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/css/camera.css | grep -q 08b27fb3571128382da7bf4cf9d14e213db716789938df8fe0d11668ccb4c73a
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
