#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/clock/js/clock.js
# previous-hash: abd49f19813bd13b4cc73733cd1c94c2f25949eefe5dc4612c35809cb7c5fc07
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-staged
printf '%s  %s\n' abd49f19813bd13b4cc73733cd1c94c2f25949eefe5dc4612c35809cb7c5fc07 /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js | grep -q abd49f19813bd13b4cc73733cd1c94c2f25949eefe5dc4612c35809cb7c5fc07
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
