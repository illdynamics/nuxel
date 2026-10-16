#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/icons/icon-48.png
# previous-hash: 34456be7688bdd3bf772179ddc69330f325b0007d93fc4114b9aa4fa7827b1b7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png.nuxel-staged
printf '%s  %s\n' 34456be7688bdd3bf772179ddc69330f325b0007d93fc4114b9aa4fa7827b1b7 /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-48.png | grep -q 34456be7688bdd3bf772179ddc69330f325b0007d93fc4114b9aa4fa7827b1b7
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
