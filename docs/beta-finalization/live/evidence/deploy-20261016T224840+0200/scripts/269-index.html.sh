#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/index.html
# previous-hash: 0f39c4d169765bf31d2f7943759a4d1e67571f636f7c649de3b92b617fae20fe
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-staged
printf '%s  %s\n' 0f39c4d169765bf31d2f7943759a4d1e67571f636f7c649de3b92b617fae20fe /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/index.html | grep -q 0f39c4d169765bf31d2f7943759a4d1e67571f636f7c649de3b92b617fae20fe
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
