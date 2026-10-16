#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/js/rootcontrol.js
# previous-hash: fb8d6a59dff00c10a4d5345ec47999d9cdc4475e3c404a47bb74016e47a4eb47
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-staged
printf '%s  %s\n' fb8d6a59dff00c10a4d5345ec47999d9cdc4475e3c404a47bb74016e47a4eb47 /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/rootcontrol.js | grep -q fb8d6a59dff00c10a4d5345ec47999d9cdc4475e3c404a47bb74016e47a4eb47
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
