#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/search.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/search.js
# previous-hash: b2d46748ccd1ba3e4be2257a9728236bd8102eb73ba37de496627ba3bd3015fc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/search.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/search.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/search.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/search.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/search.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/search.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/search.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/search.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/search.js /usr/share/nuxel/pwa/nuxel-home/js/search.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/search.js.nuxel-staged
printf '%s  %s\n' b2d46748ccd1ba3e4be2257a9728236bd8102eb73ba37de496627ba3bd3015fc /usr/share/nuxel/pwa/nuxel-home/js/search.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/search.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/search.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/search.js | grep -q b2d46748ccd1ba3e4be2257a9728236bd8102eb73ba37de496627ba3bd3015fc
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
