#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js
# previous-hash: 3f15bdacd9d52cff5e1d5b5a3ee7c1a390e97d01b3cf8af6ce2106f7490a7b6f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js.nuxel-staged
printf '%s  %s\n' 3f15bdacd9d52cff5e1d5b5a3ee7c1a390e97d01b3cf8af6ce2106f7490a7b6f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/js/nuxtore-catalog.js | grep -q 3f15bdacd9d52cff5e1d5b5a3ee7c1a390e97d01b3cf8af6ce2106f7490a7b6f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
