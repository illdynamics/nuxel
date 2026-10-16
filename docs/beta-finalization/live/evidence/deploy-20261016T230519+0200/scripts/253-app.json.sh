#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/app.json
# previous-hash: 4fc00cbead3dc346f644c43c22541082adddfa461f7dfb1d4e9462bd57719469
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json.nuxel-staged
printf '%s  %s\n' 4fc00cbead3dc346f644c43c22541082adddfa461f7dfb1d4e9462bd57719469 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/app.json | grep -q 4fc00cbead3dc346f644c43c22541082adddfa461f7dfb1d4e9462bd57719469
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
