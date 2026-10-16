#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/icons/icon-72.png
# previous-hash: 27e890f30d925bf9fa08b4d1ea4ad6c4721530f3dda9077eb4d0aa4fb8898417
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png.nuxel-staged
printf '%s  %s\n' 27e890f30d925bf9fa08b4d1ea4ad6c4721530f3dda9077eb4d0aa4fb8898417 /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-72.png | grep -q 27e890f30d925bf9fa08b4d1ea4ad6c4721530f3dda9077eb4d0aa4fb8898417
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
