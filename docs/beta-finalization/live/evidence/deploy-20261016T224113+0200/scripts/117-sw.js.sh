#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/clock/sw.js
# previous-hash: 88273ab4d76b5a0c0999c515852e30dd2c0da8a45818ac5ed76fd80141b09784
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js.nuxel-staged
printf '%s  %s\n' 88273ab4d76b5a0c0999c515852e30dd2c0da8a45818ac5ed76fd80141b09784 /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/sw.js | grep -q 88273ab4d76b5a0c0999c515852e30dd2c0da8a45818ac5ed76fd80141b09784
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
