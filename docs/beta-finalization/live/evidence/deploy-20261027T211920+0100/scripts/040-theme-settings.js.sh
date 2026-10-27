#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/theme-settings.js
# previous-hash: 67579b9a7719bca818585463a21f204637b27d8464ca722948fe0bfa52147eb3
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-staged
printf '%s  %s\n' 67579b9a7719bca818585463a21f204637b27d8464ca722948fe0bfa52147eb3 /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/theme-settings.js | grep -q 67579b9a7719bca818585463a21f204637b27d8464ca722948fe0bfa52147eb3
echo INSTALL-OK
