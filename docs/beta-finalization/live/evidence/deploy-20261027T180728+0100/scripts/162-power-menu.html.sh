#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/power-menu.html
# previous-hash: e4a0f55becbad9015fd70a6ed2c37790131e93c1ce8032724ef2b1b8dafa052f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback.pre-deploy-20261027T180728-2189607 /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback.pre-deploy-20261027T180728-2189607 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback.pre-deploy-20261027T180728-2189607; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-staged
printf '%s  %s\n' e4a0f55becbad9015fd70a6ed2c37790131e93c1ce8032724ef2b1b8dafa052f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html | grep -q e4a0f55becbad9015fd70a6ed2c37790131e93c1ce8032724ef2b1b8dafa052f
echo INSTALL-OK
