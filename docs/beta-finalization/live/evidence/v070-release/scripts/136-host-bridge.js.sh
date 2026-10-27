#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/host-bridge.js
# previous-hash: 35d18f88f5f9564a9a1ee41027968f9c3227549b2689f5be31b9d7f08d9e6762
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged
printf '%s  %s\n' 35d18f88f5f9564a9a1ee41027968f9c3227549b2689f5be31b9d7f08d9e6762 /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js | grep -q 35d18f88f5f9564a9a1ee41027968f9c3227549b2689f5be31b9d7f08d9e6762
echo INSTALL-OK
