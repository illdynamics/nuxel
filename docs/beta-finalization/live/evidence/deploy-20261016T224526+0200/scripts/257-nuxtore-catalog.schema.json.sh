#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json
# previous-hash: 6a9cc0115695573987f7378e1898b7a9b7a73e2c515535cb3b63ac9732511caf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json.nuxel-staged
printf '%s  %s\n' 6a9cc0115695573987f7378e1898b7a9b7a73e2c515535cb3b63ac9732511caf /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/nuxtore-catalog.schema.json | grep -q 6a9cc0115695573987f7378e1898b7a9b7a73e2c515535cb3b63ac9732511caf
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
