#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/system-monitor.js
# previous-hash: dfac5c203d0c9c25bc620e6397f10132dd1a21e4e013d018d30143ab33643f37
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-staged
printf '%s  %s\n' dfac5c203d0c9c25bc620e6397f10132dd1a21e4e013d018d30143ab33643f37 /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/system-monitor.js | grep -q dfac5c203d0c9c25bc620e6397f10132dd1a21e4e013d018d30143ab33643f37
echo INSTALL-OK
