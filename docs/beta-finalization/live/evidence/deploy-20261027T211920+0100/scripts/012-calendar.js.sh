#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/js/calendar.js
# previous-hash: 2d85f926248014c2dedd8be531130589e1e3c62900777501ec196fa300a320de
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-staged
printf '%s  %s\n' 2d85f926248014c2dedd8be531130589e1e3c62900777501ec196fa300a320de /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/js/calendar.js | grep -q 2d85f926248014c2dedd8be531130589e1e3c62900777501ec196fa300a320de
echo INSTALL-OK
