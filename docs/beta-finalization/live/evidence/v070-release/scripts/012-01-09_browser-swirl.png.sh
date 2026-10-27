#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png
# previous-hash: d29c012158ec6a85d7375cfc475d9e9feab44842b7b473710f053419023ed1c1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-staged
printf '%s  %s\n' d29c012158ec6a85d7375cfc475d9e9feab44842b7b473710f053419023ed1c1 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/01-09_browser-swirl.png | grep -q d29c012158ec6a85d7375cfc475d9e9feab44842b7b473710f053419023ed1c1
echo INSTALL-OK
