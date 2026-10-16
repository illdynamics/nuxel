#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/devmgmt/js/devmgmt.js
# previous-hash: 2920edaa593c438323fdbbacea52f29e3397039673fbd74a1b3d67d5d58b36bc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js.nuxel-staged
printf '%s  %s\n' 2920edaa593c438323fdbbacea52f29e3397039673fbd74a1b3d67d5d58b36bc /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/devmgmt/js/devmgmt.js | grep -q 2920edaa593c438323fdbbacea52f29e3397039673fbd74a1b3d67d5d58b36bc
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
