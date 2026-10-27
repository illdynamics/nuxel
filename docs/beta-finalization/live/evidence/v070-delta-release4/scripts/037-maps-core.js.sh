#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-common/maps-core.js (service: None, risk: low)
# staged source: pwa/nuxel-common/maps-core.js
# previous-hash: 2ad0cbd20d4553118101ccafadabcb9d3dba0647eec2de035465fedca89bf53a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-rollback.pre-v070-delta-release4 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-rollback.pre-v070-delta-release4 /usr/share/nuxel/pwa/nuxel-common/maps-core.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/maps-core.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/maps-core.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/maps-core.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/maps-core.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/maps-core.js /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/maps-core.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-rollback.pre-v070-delta-release4 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/maps-core.js /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-rollback.pre-v070-delta-release4; fi
test -f /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-staged
printf '%s  %s\n' 2ad0cbd20d4553118101ccafadabcb9d3dba0647eec2de035465fedca89bf53a /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/maps-core.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/maps-core.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/maps-core.js | grep -q 2ad0cbd20d4553118101ccafadabcb9d3dba0647eec2de035465fedca89bf53a
echo INSTALL-OK
