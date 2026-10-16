#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/sw.js
# previous-hash: 5e8cab37df9ee5d1bc3198c70db4c4652aa68bc39a266e65cba0a3c49f8e66d6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js.nuxel-staged
printf '%s  %s\n' 5e8cab37df9ee5d1bc3198c70db4c4652aa68bc39a266e65cba0a3c49f8e66d6 /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/sw.js | grep -q 5e8cab37df9ee5d1bc3198c70db4c4652aa68bc39a266e65cba0a3c49f8e66d6
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
