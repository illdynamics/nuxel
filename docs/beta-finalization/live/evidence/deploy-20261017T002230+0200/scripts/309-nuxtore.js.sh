#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/js/nuxtore.js
# previous-hash: 9b31c07fdea6493edf638795bc143dc04c32e411ceead0a244dc8f0a20d78f74
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js.nuxel-staged
printf '%s  %s\n' 9b31c07fdea6493edf638795bc143dc04c32e411ceead0a244dc8f0a20d78f74 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore.js | grep -q 9b31c07fdea6493edf638795bc143dc04c32e411ceead0a244dc8f0a20d78f74
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
