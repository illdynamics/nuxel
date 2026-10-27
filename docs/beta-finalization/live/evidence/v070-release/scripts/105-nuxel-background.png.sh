#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/nuxel-background.png
# previous-hash: 6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-staged
printf '%s  %s\n' 6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png | grep -q 6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29
echo INSTALL-OK
