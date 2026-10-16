#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/icons/icon-192.png
# previous-hash: b1f6de6b2d6b78598a0cc2af35079162bd1ba8ca2b7d770c4a7f3f72fe9473f7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png.nuxel-staged
printf '%s  %s\n' b1f6de6b2d6b78598a0cc2af35079162bd1ba8ca2b7d770c4a7f3f72fe9473f7 /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-192.png | grep -q b1f6de6b2d6b78598a0cc2af35079162bd1ba8ca2b7d770c4a7f3f72fe9473f7
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
