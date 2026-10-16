#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/browser/sw.js
# previous-hash: 4ab0f1ac905e79755e5c6f3f5e83323ca14ebb9a3688d435e17f3a52c90dab98
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js.nuxel-staged
printf '%s  %s\n' 4ab0f1ac905e79755e5c6f3f5e83323ca14ebb9a3688d435e17f3a52c90dab98 /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/browser/sw.js | grep -q 4ab0f1ac905e79755e5c6f3f5e83323ca14ebb9a3688d435e17f3a52c90dab98
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
