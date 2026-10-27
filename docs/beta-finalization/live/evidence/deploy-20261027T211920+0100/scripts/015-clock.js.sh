#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/clock/js/clock.js
# previous-hash: 00ee4312bf49146c6fb9d341aeb6396a71799e867d31199a8fb32eb2026a3201
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-staged
printf '%s  %s\n' 00ee4312bf49146c6fb9d341aeb6396a71799e867d31199a8fb32eb2026a3201 /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/js/clock.js | grep -q 00ee4312bf49146c6fb9d341aeb6396a71799e867d31199a8fb32eb2026a3201
echo INSTALL-OK
