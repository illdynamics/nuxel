#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/home-settings.js
# previous-hash: 6838ce96322e416c2b3c1115c429b434743d45e20bab900188da8e26f63a7403
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged
printf '%s  %s\n' 6838ce96322e416c2b3c1115c429b434743d45e20bab900188da8e26f63a7403 /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/home-settings.js | grep -q 6838ce96322e416c2b3c1115c429b434743d45e20bab900188da8e26f63a7403
echo INSTALL-OK
