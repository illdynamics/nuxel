#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calculator/manifest.json
# previous-hash: af17432ddd6bb5eb86b7e20b7572f07045714cf2f137af65adb28bd346de9333
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json.nuxel-staged
printf '%s  %s\n' af17432ddd6bb5eb86b7e20b7572f07045714cf2f137af65adb28bd346de9333 /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json | grep -q af17432ddd6bb5eb86b7e20b7572f07045714cf2f137af65adb28bd346de9333
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calculator/manifest.json; systemctl restart nuxel-web; fi
