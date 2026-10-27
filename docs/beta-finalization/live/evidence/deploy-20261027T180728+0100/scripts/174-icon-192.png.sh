#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console/icons/icon-192.png
# previous-hash: e7cdb228b7ceb3baf3218edd9f7c269a179ec7f915be030765913a11ca0a2160
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-staged
printf '%s  %s\n' e7cdb228b7ceb3baf3218edd9f7c269a179ec7f915be030765913a11ca0a2160 /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-192.png | grep -q e7cdb228b7ceb3baf3218edd9f7c269a179ec7f915be030765913a11ca0a2160
echo INSTALL-OK
