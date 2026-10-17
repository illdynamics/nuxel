#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/sw.js
# previous-hash: 4e6d1222ea4563c02ddd384e1a36aadf39ebe19fbbcad768cb80b54905f50c1c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js.nuxel-staged
printf '%s  %s\n' 4e6d1222ea4563c02ddd384e1a36aadf39ebe19fbbcad768cb80b54905f50c1c /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/sw.js | grep -q 4e6d1222ea4563c02ddd384e1a36aadf39ebe19fbbcad768cb80b54905f50c1c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
