#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/qs.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/qs.js
# previous-hash: e45053b26e569b7b9b21ca53e17a7b71ea29c2744d9a6b0812996179933fdafe
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/qs.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/qs.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/qs.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/qs.js /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged
printf '%s  %s\n' e45053b26e569b7b9b21ca53e17a7b71ea29c2744d9a6b0812996179933fdafe /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/qs.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/qs.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/qs.js | grep -q e45053b26e569b7b9b21ca53e17a7b71ea29c2744d9a6b0812996179933fdafe
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
