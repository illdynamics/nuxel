#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/icons/icon-128.png
# previous-hash: dc24f54c0bb9bfd96049ea9b45cb1be57a329618b4ffb79099cae49411d87f54
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' dc24f54c0bb9bfd96049ea9b45cb1be57a329618b4ffb79099cae49411d87f54 /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/icons/icon-128.png | grep -q dc24f54c0bb9bfd96049ea9b45cb1be57a329618b4ffb79099cae49411d87f54
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
