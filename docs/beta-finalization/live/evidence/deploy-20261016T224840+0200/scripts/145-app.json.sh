#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/app.json
# previous-hash: 0d841b0639ec4745165c9829da507e2a575371a0060136fa5b171dfdfe39e59f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json.nuxel-staged
printf '%s  %s\n' 0d841b0639ec4745165c9829da507e2a575371a0060136fa5b171dfdfe39e59f /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/app.json | grep -q 0d841b0639ec4745165c9829da507e2a575371a0060136fa5b171dfdfe39e59f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
