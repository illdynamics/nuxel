#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-common/bridge.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/bridge.js
# previous-hash: 75dd178ccdd9b8b886c95392f551d66dbc78e764df4ae64dc1302fd3d51bb454
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-common/bridge.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge.js /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged
printf '%s  %s\n' 75dd178ccdd9b8b886c95392f551d66dbc78e764df4ae64dc1302fd3d51bb454 /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge.js | grep -q 75dd178ccdd9b8b886c95392f551d66dbc78e764df4ae64dc1302fd3d51bb454
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/bridge.js)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
echo INSTALL-OK
