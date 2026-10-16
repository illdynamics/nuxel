#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/manifest.json
# previous-hash: ab8264e56e3e61062e1795995e86db69dbf6b8e9f8dd10f4570d7e550e1db008
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json.nuxel-staged
printf '%s  %s\n' ab8264e56e3e61062e1795995e86db69dbf6b8e9f8dd10f4570d7e550e1db008 /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/manifest.json | grep -q ab8264e56e3e61062e1795995e86db69dbf6b8e9f8dd10f4570d7e550e1db008
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
