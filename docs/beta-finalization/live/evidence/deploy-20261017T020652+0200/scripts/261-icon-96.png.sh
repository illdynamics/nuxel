#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/icons/icon-96.png
# previous-hash: 241d393d0a88a5daaf990a3965eb01d48835769e548901ae7bebaf5244ddf30f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png.nuxel-staged
printf '%s  %s\n' 241d393d0a88a5daaf990a3965eb01d48835769e548901ae7bebaf5244ddf30f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon-96.png | grep -q 241d393d0a88a5daaf990a3965eb01d48835769e548901ae7bebaf5244ddf30f
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
