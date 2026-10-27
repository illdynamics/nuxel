#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png
# previous-hash: f516db8052ac18b7895c12bc13c874d1156344d4e3684eafe62af8581fd0e27b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-staged
printf '%s  %s\n' f516db8052ac18b7895c12bc13c874d1156344d4e3684eafe62af8581fd0e27b /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/13-vibrate.png | grep -q f516db8052ac18b7895c12bc13c874d1156344d4e3684eafe62af8581fd0e27b
echo INSTALL-OK
