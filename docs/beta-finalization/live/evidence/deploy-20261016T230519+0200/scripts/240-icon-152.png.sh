#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/icons/icon-152.png
# previous-hash: e5a0c263a06d0b1c55754192c694cfb632243f33cbf332a30a5e431214c4173f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png.nuxel-staged
printf '%s  %s\n' e5a0c263a06d0b1c55754192c694cfb632243f33cbf332a30a5e431214c4173f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-152.png | grep -q e5a0c263a06d0b1c55754192c694cfb632243f33cbf332a30a5e431214c4173f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
