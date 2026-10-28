#!/bin/sh
# Lockscreen touch warning, battery guard, wider unlock band and filter-free idle rendering -> /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/status-bar.js
# previous-hash: 23030cef1e8681333d8316e3af5ccefb899e08aedc8ac306a1d672faa9a1acff
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-deploy-20261027T222442-2425280 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-deploy-20261027T222442-2425280 /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-deploy-20261027T222442-2425280 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-deploy-20261027T222442-2425280; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged
printf '%s  %s\n' 23030cef1e8681333d8316e3af5ccefb899e08aedc8ac306a1d672faa9a1acff /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js | grep -q 23030cef1e8681333d8316e3af5ccefb899e08aedc8ac306a1d672faa9a1acff
echo INSTALL-OK
