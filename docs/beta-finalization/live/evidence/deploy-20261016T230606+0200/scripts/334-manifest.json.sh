#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/manifest.json
# previous-hash: de2a3bcdafc2b7616930d2a641a88c3e2eb4780d73ab14bdc4a24d437132a1f2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-staged
printf '%s  %s\n' de2a3bcdafc2b7616930d2a641a88c3e2eb4780d73ab14bdc4a24d437132a1f2 /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json | grep -q de2a3bcdafc2b7616930d2a641a88c3e2eb4780d73ab14bdc4a24d437132a1f2
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
