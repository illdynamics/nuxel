#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/icons/icon-512.png
# previous-hash: 7912ca6ee26a8ab56d13ed99c0cd1325937ae2ce2efe51fdaefe8a67d585fadf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png.nuxel-staged
printf '%s  %s\n' 7912ca6ee26a8ab56d13ed99c0cd1325937ae2ce2efe51fdaefe8a67d585fadf /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/icons/icon-512.png | grep -q 7912ca6ee26a8ab56d13ed99c0cd1325937ae2ce2efe51fdaefe8a67d585fadf
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
