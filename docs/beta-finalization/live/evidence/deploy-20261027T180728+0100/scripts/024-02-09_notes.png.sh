#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png
# previous-hash: 030d30414a1648135912e7353ec4ff6f00a8fcb5c5d2a88f726215defd62e283
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-staged
printf '%s  %s\n' 030d30414a1648135912e7353ec4ff6f00a8fcb5c5d2a88f726215defd62e283 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/02-09_notes.png | grep -q 030d30414a1648135912e7353ec4ff6f00a8fcb5c5d2a88f726215defd62e283
echo INSTALL-OK
