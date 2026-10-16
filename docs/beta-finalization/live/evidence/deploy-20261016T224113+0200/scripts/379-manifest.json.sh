#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/manifest.json
# previous-hash: 76f3cb6f2bc8fabb05964b26268ddd3de8f0064af8146da5d61c7751bbc6d543
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json.nuxel-staged
printf '%s  %s\n' 76f3cb6f2bc8fabb05964b26268ddd3de8f0064af8146da5d61c7751bbc6d543 /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/manifest.json | grep -q 76f3cb6f2bc8fabb05964b26268ddd3de8f0064af8146da5d61c7751bbc6d543
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
