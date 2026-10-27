#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png
# previous-hash: b10a79025ac113dc47462c87e1abfcd5893f3e91ef2ee90647ead42b6b4873c1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-staged
printf '%s  %s\n' b10a79025ac113dc47462c87e1abfcd5893f3e91ef2ee90647ead42b6b4873c1 /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/branding/nuxel-applications-icon-pack/06-04_casting-screen.png | grep -q b10a79025ac113dc47462c87e1abfcd5893f3e91ef2ee90647ead42b6b4873c1
echo INSTALL-OK
