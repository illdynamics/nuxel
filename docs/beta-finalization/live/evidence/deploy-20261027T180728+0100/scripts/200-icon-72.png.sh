#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/maps/icons/icon-72.png
# previous-hash: c9a4234cddf234e5acd859a5f1f110ead1a70418480e26a912220f1920eab182
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-staged
printf '%s  %s\n' c9a4234cddf234e5acd859a5f1f110ead1a70418480e26a912220f1920eab182 /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-72.png | grep -q c9a4234cddf234e5acd859a5f1f110ead1a70418480e26a912220f1920eab182
echo INSTALL-OK
