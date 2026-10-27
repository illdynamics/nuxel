#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/button-middle.png
# previous-hash: c9b34ac7e3a387626a5ee6694519b779bced64bf32869be096f73cf4c7011fc1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-staged
printf '%s  %s\n' c9b34ac7e3a387626a5ee6694519b779bced64bf32869be096f73cf4c7011fc1 /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-middle.png | grep -q c9b34ac7e3a387626a5ee6694519b779bced64bf32869be096f73cf4c7011fc1
echo INSTALL-OK
