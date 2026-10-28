#!/bin/sh
# Lockscreen touch warning, battery guard, wider unlock band and filter-free idle rendering -> /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/lockscreen.js
# previous-hash: 88d0034bd0648ed626dcb2f3cf2010be0332e2331f6054d4ff80295146f0f522
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T222436-2425021 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T222436-2425021 /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T222436-2425021 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-rollback.pre-deploy-20261027T222436-2425021; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-staged
printf '%s  %s\n' 88d0034bd0648ed626dcb2f3cf2010be0332e2331f6054d4ff80295146f0f522 /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/lockscreen.js | grep -q 88d0034bd0648ed626dcb2f3cf2010be0332e2331f6054d4ff80295146f0f522
echo INSTALL-OK
