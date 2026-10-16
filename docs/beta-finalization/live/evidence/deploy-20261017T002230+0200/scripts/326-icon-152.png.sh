#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/icons/icon-152.png
# previous-hash: debe6f2a711d23af22d9ac93ea7546b24140dbcc4cbab2372038b37ffeca02e9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png.nuxel-staged
printf '%s  %s\n' debe6f2a711d23af22d9ac93ea7546b24140dbcc4cbab2372038b37ffeca02e9 /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/icons/icon-152.png | grep -q debe6f2a711d23af22d9ac93ea7546b24140dbcc4cbab2372038b37ffeca02e9
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
