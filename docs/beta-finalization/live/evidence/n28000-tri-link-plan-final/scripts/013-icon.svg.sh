#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/console/icons/icon.svg
# previous-hash: dc2d5a956cf51c38fd162facbe5d52127df1f1e892ef10c91841ac597d41b878
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-rollback.pre-deploy-20261027T163854-2125055 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-rollback.pre-deploy-20261027T163854-2125055 /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-rollback.pre-deploy-20261027T163854-2125055 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-rollback.pre-deploy-20261027T163854-2125055; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-staged
printf '%s  %s\n' dc2d5a956cf51c38fd162facbe5d52127df1f1e892ef10c91841ac597d41b878 /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon.svg | grep -q dc2d5a956cf51c38fd162facbe5d52127df1f1e892ef10c91841ac597d41b878
echo INSTALL-OK
