#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/apps.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/apps.js
# previous-hash: 4ec589c1827d9e6bafcd04212f082fae3644dcc2fcaa54a903750b318cea8bc8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-home/js/apps.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/apps.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged
printf '%s  %s\n' 4ec589c1827d9e6bafcd04212f082fae3644dcc2fcaa54a903750b318cea8bc8 /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/apps.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js | grep -q 4ec589c1827d9e6bafcd04212f082fae3644dcc2fcaa54a903750b318cea8bc8
echo INSTALL-OK
