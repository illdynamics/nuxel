#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/nuxel-bottom-bar2.png
# previous-hash: be60ece34adcf0179d1a94e4cbca309bd8f9bd629c14aedbd00d6b32d1ccf0e3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-staged
printf '%s  %s\n' be60ece34adcf0179d1a94e4cbca309bd8f9bd629c14aedbd00d6b32d1ccf0e3 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-bottom-bar2.png | grep -q be60ece34adcf0179d1a94e4cbca309bd8f9bd629c14aedbd00d6b32d1ccf0e3
echo INSTALL-OK
