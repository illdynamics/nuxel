#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/button-right.png
# previous-hash: 23257499b1617e95afd9b02a1bd99c86633f13e9f1f83d781b315d94873ee921
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-staged
printf '%s  %s\n' 23257499b1617e95afd9b02a1bd99c86633f13e9f1f83d781b315d94873ee921 /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/button-right.png | grep -q 23257499b1617e95afd9b02a1bd99c86633f13e9f1f83d781b315d94873ee921
echo INSTALL-OK
