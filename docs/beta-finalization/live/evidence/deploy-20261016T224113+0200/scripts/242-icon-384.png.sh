#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/icons/icon-384.png
# previous-hash: 312a8a72157761b08fbc1f9d6df85af6bf34daf0c7cc7cf347f20792bdbe222c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png.nuxel-staged
printf '%s  %s\n' 312a8a72157761b08fbc1f9d6df85af6bf34daf0c7cc7cf347f20792bdbe222c /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-384.png | grep -q 312a8a72157761b08fbc1f9d6df85af6bf34daf0c7cc7cf347f20792bdbe222c
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
