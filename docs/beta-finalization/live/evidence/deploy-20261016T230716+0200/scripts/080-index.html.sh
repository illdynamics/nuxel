#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/camera-gallery/index.html
# previous-hash: b8a5a3d5e141d692d6d499891e961bccba937be22a014e3d8404c6ca10ec4ccd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-staged
printf '%s  %s\n' b8a5a3d5e141d692d6d499891e961bccba937be22a014e3d8404c6ca10ec4ccd /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/camera-gallery/index.html | grep -q b8a5a3d5e141d692d6d499891e961bccba937be22a014e3d8404c6ca10ec4ccd
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
