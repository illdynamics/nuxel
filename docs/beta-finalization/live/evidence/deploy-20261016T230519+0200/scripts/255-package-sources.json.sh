#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/catalog/package-sources.json
# previous-hash: 2ce5e49d77eb39edb89281378bf777f98689a0a299d1e5c7b24bd5615e51c282
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json.nuxel-staged
printf '%s  %s\n' 2ce5e49d77eb39edb89281378bf777f98689a0a299d1e5c7b24bd5615e51c282 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/catalog/package-sources.json | grep -q 2ce5e49d77eb39edb89281378bf777f98689a0a299d1e5c7b24bd5615e51c282
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
