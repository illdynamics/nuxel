#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png
# previous-hash: 34e095eeee848c5d14161f937410a8e3ab40bac1b3ed2d57f9b3e1bf18c3e0a1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-staged
printf '%s  %s\n' 34e095eeee848c5d14161f937410a8e3ab40bac1b3ed2d57f9b3e1bf18c3e0a1 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-quicksettings-icon-pack/29-terminal-alternate.png | grep -q 34e095eeee848c5d14161f937410a8e3ab40bac1b3ed2d57f9b3e1bf18c3e0a1
echo INSTALL-OK
