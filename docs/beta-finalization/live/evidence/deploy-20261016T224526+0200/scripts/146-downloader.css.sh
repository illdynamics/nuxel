#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/css/downloader.css
# previous-hash: 9eafbb8b313733df443bb61b26c9de9990ec7c99a63a1a0064f9adc5369817c1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css.nuxel-staged
printf '%s  %s\n' 9eafbb8b313733df443bb61b26c9de9990ec7c99a63a1a0064f9adc5369817c1 /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/css/downloader.css | grep -q 9eafbb8b313733df443bb61b26c9de9990ec7c99a63a1a0064f9adc5369817c1
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
