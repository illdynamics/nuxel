#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png
# previous-hash: 2b728648ca6ce4b58522496edad7ed647fbbe85f3f385ae7f643e20deb3f9e97
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-staged
printf '%s  %s\n' 2b728648ca6ce4b58522496edad7ed647fbbe85f3f385ae7f643e20deb3f9e97 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-06_pixel-envelope.png | grep -q 2b728648ca6ce4b58522496edad7ed647fbbe85f3f385ae7f643e20deb3f9e97
echo INSTALL-OK
