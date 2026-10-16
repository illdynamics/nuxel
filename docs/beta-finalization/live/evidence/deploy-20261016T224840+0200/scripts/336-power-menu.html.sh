#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/power-menu.html
# previous-hash: e4a0f55becbad9015fd70a6ed2c37790131e93c1ce8032724ef2b1b8dafa052f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-staged
printf '%s  %s\n' e4a0f55becbad9015fd70a6ed2c37790131e93c1ce8032724ef2b1b8dafa052f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.html | grep -q e4a0f55becbad9015fd70a6ed2c37790131e93c1ce8032724ef2b1b8dafa052f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
