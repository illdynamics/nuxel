#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/js/calendar.js
# previous-hash: 4cb613aeb09efd687d99b83e03d901f20d4ecc8e6b8e28f62852cabf42ea624c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-staged
printf '%s  %s\n' 4cb613aeb09efd687d99b83e03d901f20d4ecc8e6b8e28f62852cabf42ea624c /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js | grep -q 4cb613aeb09efd687d99b83e03d901f20d4ecc8e6b8e28f62852cabf42ea624c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
