#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/host-bridge.js
# previous-hash: 35d18f88f5f9564a9a1ee41027968f9c3227549b2689f5be31b9d7f08d9e6762
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged
printf '%s  %s\n' 35d18f88f5f9564a9a1ee41027968f9c3227549b2689f5be31b9d7f08d9e6762 /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/host-bridge.js | grep -q 35d18f88f5f9564a9a1ee41027968f9c3227549b2689f5be31b9d7f08d9e6762
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
