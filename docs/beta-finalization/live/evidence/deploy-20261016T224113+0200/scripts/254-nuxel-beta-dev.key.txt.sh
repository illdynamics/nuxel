#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt
# previous-hash: 469fd12add991da2fb3d287720a945460ce3f6c6b728dc78f801522a9488fbe4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt.nuxel-staged
printf '%s  %s\n' 469fd12add991da2fb3d287720a945460ce3f6c6b728dc78f801522a9488fbe4 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/keys/nuxel-beta-dev.key.txt | grep -q 469fd12add991da2fb3d287720a945460ce3f6c6b728dc78f801522a9488fbe4
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
