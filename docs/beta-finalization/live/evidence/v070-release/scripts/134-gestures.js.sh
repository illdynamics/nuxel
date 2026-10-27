#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/gestures.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/gestures.js
# previous-hash: c56a79782bc39f3f27d299049c40c94d4fca501c07a7dff2232b7b3c3938eb31
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/gestures.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/gestures.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/gestures.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/gestures.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/gestures.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/gestures.js /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/gestures.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/gestures.js /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-staged
printf '%s  %s\n' c56a79782bc39f3f27d299049c40c94d4fca501c07a7dff2232b7b3c3938eb31 /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/gestures.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/gestures.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/gestures.js | grep -q c56a79782bc39f3f27d299049c40c94d4fca501c07a7dff2232b7b3c3938eb31
echo INSTALL-OK
