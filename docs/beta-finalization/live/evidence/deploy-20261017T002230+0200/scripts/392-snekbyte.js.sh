#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/js/snekbyte.js
# previous-hash: 3faea1a33f06d93c2b7365a8d7832199dbd6a84cf79818e25209a5405c16b5eb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-staged
printf '%s  %s\n' 3faea1a33f06d93c2b7365a8d7832199dbd6a84cf79818e25209a5405c16b5eb /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/js/snekbyte.js | grep -q 3faea1a33f06d93c2b7365a8d7832199dbd6a84cf79818e25209a5405c16b5eb
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
