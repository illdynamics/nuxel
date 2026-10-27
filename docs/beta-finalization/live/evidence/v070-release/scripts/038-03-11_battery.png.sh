#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png
# previous-hash: 5a58228fc231c5ee45e5d67f1f9fb2b2a83ce82563ab808c1470d090429567f8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-staged
printf '%s  %s\n' 5a58228fc231c5ee45e5d67f1f9fb2b2a83ce82563ab808c1470d090429567f8 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/03-11_battery.png | grep -q 5a58228fc231c5ee45e5d67f1f9fb2b2a83ce82563ab808c1470d090429567f8
echo INSTALL-OK
