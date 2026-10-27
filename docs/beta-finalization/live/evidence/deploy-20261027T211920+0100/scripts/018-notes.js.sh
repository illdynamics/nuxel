#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/js/notes.js
# previous-hash: 7c8bc45ac8d89ee2c352486e5dcc6e650d0999ad86f618001a8374fc8ff2e125
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-staged
printf '%s  %s\n' 7c8bc45ac8d89ee2c352486e5dcc6e650d0999ad86f618001a8374fc8ff2e125 /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes.js | grep -q 7c8bc45ac8d89ee2c352486e5dcc6e650d0999ad86f618001a8374fc8ff2e125
echo INSTALL-OK
