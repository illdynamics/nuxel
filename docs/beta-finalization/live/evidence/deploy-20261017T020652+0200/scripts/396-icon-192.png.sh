#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/terminal/icons/icon-192.png
# previous-hash: 9e218d5187268dc5f727df51e9dce712f71ee24d5ae3e6968ef41393deffec9c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png.nuxel-staged
printf '%s  %s\n' 9e218d5187268dc5f727df51e9dce712f71ee24d5ae3e6968ef41393deffec9c /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/terminal/icons/icon-192.png | grep -q 9e218d5187268dc5f727df51e9dce712f71ee24d5ae3e6968ef41393deffec9c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
