#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/safe-zones.js
# previous-hash: 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged
printf '%s  %s\n' 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js | grep -q 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f
echo INSTALL-OK
