#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calculator/sw.js
# previous-hash: 9914b876a073889f98bb828d33ec91d535552c5c7a28b00e93e8fafbba4e41b5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js.nuxel-staged
printf '%s  %s\n' 9914b876a073889f98bb828d33ec91d535552c5c7a28b00e93e8fafbba4e41b5 /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/sw.js | grep -q 9914b876a073889f98bb828d33ec91d535552c5c7a28b00e93e8fafbba4e41b5
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
