#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/maps/sw.js
# previous-hash: 69f7330a125749a6774c53f3048e9f96b223fad995b76bd24b610d9613d9a72d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback.pre-deploy-20261027T182142-2202036 /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-rollback.pre-deploy-20261027T182142-2202036; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-staged
printf '%s  %s\n' 69f7330a125749a6774c53f3048e9f96b223fad995b76bd24b610d9613d9a72d /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/sw.js | grep -q 69f7330a125749a6774c53f3048e9f96b223fad995b76bd24b610d9613d9a72d
echo INSTALL-OK
