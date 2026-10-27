#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/lockscreen.js
# previous-hash: 94849e33ab9862c986d15d3f11d84d2dfaeeb104cc4e0988da391eafc2e4c517
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-staged
printf '%s  %s\n' 94849e33ab9862c986d15d3f11d84d2dfaeeb104cc4e0988da391eafc2e4c517 /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js | grep -q 94849e33ab9862c986d15d3f11d84d2dfaeeb104cc4e0988da391eafc2e4c517
echo INSTALL-OK
