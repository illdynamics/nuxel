#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/icons/icon-144.png
# previous-hash: a3ecb9f23cb75d296c928cb4fe9696b42038cbaccb1dd5f3c7ef7dc176905a42
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png.nuxel-staged
printf '%s  %s\n' a3ecb9f23cb75d296c928cb4fe9696b42038cbaccb1dd5f3c7ef7dc176905a42 /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-144.png | grep -q a3ecb9f23cb75d296c928cb4fe9696b42038cbaccb1dd5f3c7ef7dc176905a42
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
