#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/js/app.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/js/app.js
# previous-hash: ac5ae9490bd0af69812c1372a2e5f30fc52c072281976c1e4545059ff8d9509f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-home/js/app.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/app.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/app.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged
printf '%s  %s\n' ac5ae9490bd0af69812c1372a2e5f30fc52c072281976c1e4545059ff8d9509f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/app.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/app.js | grep -q ac5ae9490bd0af69812c1372a2e5f30fc52c072281976c1e4545059ff8d9509f
echo INSTALL-OK
