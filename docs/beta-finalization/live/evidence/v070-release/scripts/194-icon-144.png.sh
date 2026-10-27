#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/maps/icons/icon-144.png
# previous-hash: 1ba09a6097fcb7bbc97ffe4fee358013a257f5e881fb0d23d2cb6942f61458ff
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-staged
printf '%s  %s\n' 1ba09a6097fcb7bbc97ffe4fee358013a257f5e881fb0d23d2cb6942f61458ff /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/icons/icon-144.png | grep -q 1ba09a6097fcb7bbc97ffe4fee358013a257f5e881fb0d23d2cb6942f61458ff
echo INSTALL-OK
