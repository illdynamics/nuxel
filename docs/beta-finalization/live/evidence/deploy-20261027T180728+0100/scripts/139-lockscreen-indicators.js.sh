#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/lockscreen-indicators.js
# previous-hash: fb9627ee7bb88bd22de05b49ceb418445779aaac182c88f967b0edf7114eeee7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-staged
printf '%s  %s\n' fb9627ee7bb88bd22de05b49ceb418445779aaac182c88f967b0edf7114eeee7 /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js | grep -q fb9627ee7bb88bd22de05b49ceb418445779aaac182c88f967b0edf7114eeee7
echo INSTALL-OK
