#!/bin/sh
# systemd unit env pins + bridge-version.json + shared PWA bridge honesty fallback -> /usr/share/nuxel/pwa/nuxel-common/bridge.js (service: None, risk: medium)
# staged source: pwa/nuxel-common/bridge.js
# previous-hash: 1b409e04facb7f185c7bdbf810082251fd802246444c2ca3d94f7c9877b0b75e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000 /usr/share/nuxel/pwa/nuxel-common/bridge.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged
printf '%s  %s\n' 1b409e04facb7f185c7bdbf810082251fd802246444c2ca3d94f7c9877b0b75e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | grep -q 1b409e04facb7f185c7bdbf810082251fd802246444c2ca3d94f7c9877b0b75e
echo INSTALL-OK
