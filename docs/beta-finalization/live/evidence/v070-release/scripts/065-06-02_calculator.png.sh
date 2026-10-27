#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png
# previous-hash: a04e185440a91d1d1ea4b86d4c0d0793b62fbddbdd296e2208af13d598ed2a11
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-staged
printf '%s  %s\n' a04e185440a91d1d1ea4b86d4c0d0793b62fbddbdd296e2208af13d598ed2a11 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-02_calculator.png | grep -q a04e185440a91d1d1ea4b86d4c0d0793b62fbddbdd296e2208af13d598ed2a11
echo INSTALL-OK
