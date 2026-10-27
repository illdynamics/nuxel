#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png
# previous-hash: 9a9b67f421d0ed2f83c086816b078c3be85bfdc3fc76a3743dd13c8509b2fda1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-staged
printf '%s  %s\n' 9a9b67f421d0ed2f83c086816b078c3be85bfdc3fc76a3743dd13c8509b2fda1 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/04-bluetooth.png | grep -q 9a9b67f421d0ed2f83c086816b078c3be85bfdc3fc76a3743dd13c8509b2fda1
echo INSTALL-OK
