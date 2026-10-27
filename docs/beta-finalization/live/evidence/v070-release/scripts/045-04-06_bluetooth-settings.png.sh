#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png
# previous-hash: 0d237de9eece6ecafa18768990e7287c7e38c34fc51728f202bef182b4167852
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-staged
printf '%s  %s\n' 0d237de9eece6ecafa18768990e7287c7e38c34fc51728f202bef182b4167852 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/04-06_bluetooth-settings.png | grep -q 0d237de9eece6ecafa18768990e7287c7e38c34fc51728f202bef182b4167852
echo INSTALL-OK
