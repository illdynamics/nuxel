#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/clock/css/clock.css
# previous-hash: 21e091b8d7c1db101fa92cfba4c43b539f024bb94983a4358b2e4b19b5cfbb64
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-staged
printf '%s  %s\n' 21e091b8d7c1db101fa92cfba4c43b539f024bb94983a4358b2e4b19b5cfbb64 /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css | grep -q 21e091b8d7c1db101fa92cfba4c43b539f024bb94983a4358b2e4b19b5cfbb64
echo INSTALL-OK
