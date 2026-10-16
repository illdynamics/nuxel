#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/sw.js
# previous-hash: 2e54bc23dfc5b5b9357728b020d13c0f612ede122f5bbc1afba7ddfeb3081ee8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js.nuxel-staged
printf '%s  %s\n' 2e54bc23dfc5b5b9357728b020d13c0f612ede122f5bbc1afba7ddfeb3081ee8 /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/sw.js | grep -q 2e54bc23dfc5b5b9357728b020d13c0f612ede122f5bbc1afba7ddfeb3081ee8
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
