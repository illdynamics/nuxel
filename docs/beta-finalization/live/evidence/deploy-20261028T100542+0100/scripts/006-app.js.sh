#!/bin/sh
# Route short Back through the bridge for native apps and close native toplevel on long Back -> /usr/share/nuxel/pwa/nuxel-home/js/app.js (service: nuxel-wayland, risk: medium)
# staged source: pwa/nuxel-home/js/app.js
# previous-hash: 4193e03f019185dc6ff780d41ee0757e0d1704a8382a641f0b1b6e654b930868
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261028T100542-2722856 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261028T100542-2722856 /usr/share/nuxel/pwa/nuxel-home/js/app.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/app.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261028T100542-2722856 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261028T100542-2722856; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged
printf '%s  %s\n' 4193e03f019185dc6ff780d41ee0757e0d1704a8382a641f0b1b6e654b930868 /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/app.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | grep -q 4193e03f019185dc6ff780d41ee0757e0d1704a8382a641f0b1b6e654b930868
echo INSTALL-OK
