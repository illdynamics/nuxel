#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json
# previous-hash: 83a174a24b1061420a510cbcdd8824b034e7af2e8e93245fef8d5270248b99d7
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json.nuxel-staged
printf '%s  %s\n' 83a174a24b1061420a510cbcdd8824b034e7af2e8e93245fef8d5270248b99d7 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json | grep -q 83a174a24b1061420a510cbcdd8824b034e7af2e8e93245fef8d5270248b99d7
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/schema/bundle.schema.json; systemctl restart nuxel-web; fi
