#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/photos/sw.js
# previous-hash: d4e1336d151af87bb1a01e7be1c3aed286b9993413abdbb00d2fab2ecf710702
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js.nuxel-staged
printf '%s  %s\n' d4e1336d151af87bb1a01e7be1c3aed286b9993413abdbb00d2fab2ecf710702 /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/photos/sw.js | grep -q d4e1336d151af87bb1a01e7be1c3aed286b9993413abdbb00d2fab2ecf710702
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
