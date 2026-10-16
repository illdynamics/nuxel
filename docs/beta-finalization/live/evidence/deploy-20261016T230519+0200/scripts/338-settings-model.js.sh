#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/settings-model.js
# previous-hash: df1fe0cb81d03d9e6a147bc26245592ccebdb92a921fafcfab1a98d708b43c38
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-staged
printf '%s  %s\n' df1fe0cb81d03d9e6a147bc26245592ccebdb92a921fafcfab1a98d708b43c38 /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js | grep -q df1fe0cb81d03d9e6a147bc26245592ccebdb92a921fafcfab1a98d708b43c38
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
