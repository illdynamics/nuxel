#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/bootlog.js
# previous-hash: d2f766a1e3e128fef72389bf99ff43953c0cea7fd54cdf78edd37a612e52ea3b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-staged
printf '%s  %s\n' d2f766a1e3e128fef72389bf99ff43953c0cea7fd54cdf78edd37a612e52ea3b /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bootlog.js | grep -q d2f766a1e3e128fef72389bf99ff43953c0cea7fd54cdf78edd37a612e52ea3b
echo INSTALL-OK
