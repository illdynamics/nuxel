#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/nuxtore/manifest.json
# previous-hash: 402bd3db566ffaeb36e76906a2f75d44ce8dcdfec6e2b4ab00a45b5dc39f44a2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json.nuxel-staged
printf '%s  %s\n' 402bd3db566ffaeb36e76906a2f75d44ce8dcdfec6e2b4ab00a45b5dc39f44a2 /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/nuxtore/manifest.json | grep -q 402bd3db566ffaeb36e76906a2f75d44ce8dcdfec6e2b4ab00a45b5dc39f44a2
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
