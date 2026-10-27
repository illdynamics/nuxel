#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/recorder/js/recorder-wav.js
# previous-hash: 0a6f9d7136dfc5887cf2e74ec6c68b56579d5878002680a5e7edf139d352230b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-staged
printf '%s  %s\n' 0a6f9d7136dfc5887cf2e74ec6c68b56579d5878002680a5e7edf139d352230b /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/recorder/js/recorder-wav.js | grep -q 0a6f9d7136dfc5887cf2e74ec6c68b56579d5878002680a5e7edf139d352230b
echo INSTALL-OK
