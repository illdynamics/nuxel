#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/icons/icon-72.png
# previous-hash: a83b5a119dcf03567f9467b85af8493a987afedf32244c79ae250fae07747996
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png.nuxel-staged
printf '%s  %s\n' a83b5a119dcf03567f9467b85af8493a987afedf32244c79ae250fae07747996 /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon-72.png | grep -q a83b5a119dcf03567f9467b85af8493a987afedf32244c79ae250fae07747996
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
