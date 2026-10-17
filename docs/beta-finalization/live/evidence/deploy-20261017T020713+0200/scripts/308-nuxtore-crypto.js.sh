#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js
# previous-hash: 5188686f876631ffa2378a355e518a3fdb3b0ba3df68d751e19982bfb1e05409
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js.nuxel-staged
printf '%s  %s\n' 5188686f876631ffa2378a355e518a3fdb3b0ba3df68d751e19982bfb1e05409 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-crypto.js | grep -q 5188686f876631ffa2378a355e518a3fdb3b0ba3df68d751e19982bfb1e05409
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
