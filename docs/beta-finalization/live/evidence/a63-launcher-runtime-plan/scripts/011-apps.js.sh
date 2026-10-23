#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/apps.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/apps.js
# previous-hash: d68efd0f8b3505a68646575f15daaf3d62842d75fe58b50a3e8752a65e198570
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/apps.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/apps.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/apps.js /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged
printf '%s  %s\n' d68efd0f8b3505a68646575f15daaf3d62842d75fe58b50a3e8752a65e198570 /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/apps.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/apps.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/apps.js | grep -q d68efd0f8b3505a68646575f15daaf3d62842d75fe58b50a3e8752a65e198570
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
