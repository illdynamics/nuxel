#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png
# previous-hash: 305639f42b9b749d964ef7dd932e984548f78ecb9a5e7b15f3cb39b9f2c437b9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-staged
printf '%s  %s\n' 305639f42b9b749d964ef7dd932e984548f78ecb9a5e7b15f3cb39b9f2c437b9 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-10_volume.png | grep -q 305639f42b9b749d964ef7dd932e984548f78ecb9a5e7b15f3cb39b9f2c437b9
echo INSTALL-OK
