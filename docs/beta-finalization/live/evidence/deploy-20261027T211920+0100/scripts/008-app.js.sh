#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-home/js/app.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/app.js
# previous-hash: 96768d638c8f6663c53d33f7fa6789bd1ea3a80eb371cd39e4a88e834c5e1889
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-home/js/app.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/app.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged
printf '%s  %s\n' 96768d638c8f6663c53d33f7fa6789bd1ea3a80eb371cd39e4a88e834c5e1889 /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/app.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | grep -q 96768d638c8f6663c53d33f7fa6789bd1ea3a80eb371cd39e4a88e834c5e1889
echo INSTALL-OK
