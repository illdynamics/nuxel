#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png
# previous-hash: 1a5bcd1ebafd71f66cb719530d81c2a73d2a83f07643500723974674841be693
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-staged
printf '%s  %s\n' 1a5bcd1ebafd71f66cb719530d81c2a73d2a83f07643500723974674841be693 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/30-quick-settings.png | grep -q 1a5bcd1ebafd71f66cb719530d81c2a73d2a83f07643500723974674841be693
echo INSTALL-OK
