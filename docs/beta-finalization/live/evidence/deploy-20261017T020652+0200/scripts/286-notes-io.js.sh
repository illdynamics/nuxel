#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/js/notes-io.js
# previous-hash: 9bb64a5257695b401b90fb2f5144cc11dced565924a2a89fc36d894a3e27bbc2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js.nuxel-staged
printf '%s  %s\n' 9bb64a5257695b401b90fb2f5144cc11dced565924a2a89fc36d894a3e27bbc2 /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/js/notes-io.js | grep -q 9bb64a5257695b401b90fb2f5144cc11dced565924a2a89fc36d894a3e27bbc2
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
