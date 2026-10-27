#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png
# previous-hash: cb2f2746a23c5fed3b270cdced2a628316e64141c6e1dd8cd9f9212bd8272851
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-staged
printf '%s  %s\n' cb2f2746a23c5fed3b270cdced2a628316e64141c6e1dd8cd9f9212bd8272851 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/05-01_root-sudo-control.png | grep -q cb2f2746a23c5fed3b270cdced2a628316e64141c6e1dd8cd9f9212bd8272851
echo INSTALL-OK
