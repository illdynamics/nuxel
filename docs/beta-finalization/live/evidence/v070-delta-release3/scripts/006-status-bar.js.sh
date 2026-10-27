#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/status-bar.js
# previous-hash: 5e6741e1f3bf02c0e31245cedd5925514d67c6347cc54c7672c68598c96c9c8f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-v070-delta-release3 /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged
printf '%s  %s\n' 5e6741e1f3bf02c0e31245cedd5925514d67c6347cc54c7672c68598c96c9c8f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js | grep -q 5e6741e1f3bf02c0e31245cedd5925514d67c6347cc54c7672c68598c96c9c8f
echo INSTALL-OK
