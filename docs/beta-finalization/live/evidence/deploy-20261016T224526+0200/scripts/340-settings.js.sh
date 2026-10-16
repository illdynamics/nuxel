#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/settings.js
# previous-hash: c243ab16e61458afc07685858ee30be857fe32590c2e6e47c3344b24ba8e517d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-staged
printf '%s  %s\n' c243ab16e61458afc07685858ee30be857fe32590c2e6e47c3344b24ba8e517d /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.js | grep -q c243ab16e61458afc07685858ee30be857fe32590c2e6e47c3344b24ba8e517d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
