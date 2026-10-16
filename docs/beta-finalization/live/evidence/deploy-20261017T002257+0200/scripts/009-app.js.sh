#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/app.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/app.js
# previous-hash: 2ba9ff8be5331b18ba0353a95ddace87edb8c4f7f368c6ca17f3113ace2d849a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/app.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/app.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged
printf '%s  %s\n' 2ba9ff8be5331b18ba0353a95ddace87edb8c4f7f368c6ca17f3113ace2d849a /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/app.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | grep -q 2ba9ff8be5331b18ba0353a95ddace87edb8c4f7f368c6ca17f3113ace2d849a
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
