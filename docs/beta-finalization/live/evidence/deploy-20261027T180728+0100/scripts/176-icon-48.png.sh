#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console/icons/icon-48.png
# previous-hash: 395200d5e20520e0c5ecfb8fa4219afde5373dc5fb775e07c751828e1330ca0b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-staged
printf '%s  %s\n' 395200d5e20520e0c5ecfb8fa4219afde5373dc5fb775e07c751828e1330ca0b /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-48.png | grep -q 395200d5e20520e0c5ecfb8fa4219afde5373dc5fb775e07c751828e1330ca0b
echo INSTALL-OK
