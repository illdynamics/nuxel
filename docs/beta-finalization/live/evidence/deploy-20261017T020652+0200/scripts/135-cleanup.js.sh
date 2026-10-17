#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/js/cleanup.js
# previous-hash: f4f2858312b548d04dae5ddfd62cb7c0584b315df3fa651f21e0f037b87c0557
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js.nuxel-staged
printf '%s  %s\n' f4f2858312b548d04dae5ddfd62cb7c0584b315df3fa651f21e0f037b87c0557 /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup.js | grep -q f4f2858312b548d04dae5ddfd62cb7c0584b315df3fa651f21e0f037b87c0557
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
