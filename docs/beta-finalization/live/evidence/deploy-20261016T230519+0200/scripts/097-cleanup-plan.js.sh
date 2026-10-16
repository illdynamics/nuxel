#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/js/cleanup-plan.js
# previous-hash: ad3f42de528a6ee07ae6cf4e7046e2ccec7864c6e1fa894e7a9f39dc8b7739a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js.nuxel-staged
printf '%s  %s\n' ad3f42de528a6ee07ae6cf4e7046e2ccec7864c6e1fa894e7a9f39dc8b7739a0 /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/js/cleanup-plan.js | grep -q ad3f42de528a6ee07ae6cf4e7046e2ccec7864c6e1fa894e7a9f39dc8b7739a0
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
