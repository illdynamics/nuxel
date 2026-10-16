#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/icons/icon-512.png
# previous-hash: d60e07a45db21d5f64832885198e948f50a311171817ff2c4bed476b4779bc5a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png.nuxel-staged
printf '%s  %s\n' d60e07a45db21d5f64832885198e948f50a311171817ff2c4bed476b4779bc5a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-512.png | grep -q d60e07a45db21d5f64832885198e948f50a311171817ff2c4bed476b4779bc5a
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
