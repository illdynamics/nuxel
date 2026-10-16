#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/power-menu.js
# previous-hash: 466e768c0a3a174584db62c67b072d3b4e910acab8697b36b8db3fa150c0a40a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged
printf '%s  %s\n' 466e768c0a3a174584db62c67b072d3b4e910acab8697b36b8db3fa150c0a40a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.js | grep -q 466e768c0a3a174584db62c67b072d3b4e910acab8697b36b8db3fa150c0a40a
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
