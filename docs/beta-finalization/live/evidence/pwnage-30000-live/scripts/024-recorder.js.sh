#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/js/recorder.js
# previous-hash: 1b7f1c80eeb3200f2a5fa265532911f83773149c54e4eab90f98bd479db01bc0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-staged
printf '%s  %s\n' 1b7f1c80eeb3200f2a5fa265532911f83773149c54e4eab90f98bd479db01bc0 /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder.js | grep -q 1b7f1c80eeb3200f2a5fa265532911f83773149c54e4eab90f98bd479db01bc0
echo INSTALL-OK
