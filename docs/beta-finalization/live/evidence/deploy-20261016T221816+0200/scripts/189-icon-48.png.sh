#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/icons/icon-48.png
# previous-hash: 6e4ecab11eb5cdb3e3c7587ca1d3911dd1af5533dac0f3289ae3602a44bdaae3
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png.nuxel-staged
printf '%s  %s\n' 6e4ecab11eb5cdb3e3c7587ca1d3911dd1af5533dac0f3289ae3602a44bdaae3 /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png | grep -q 6e4ecab11eb5cdb3e3c7587ca1d3911dd1af5533dac0f3289ae3602a44bdaae3
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-48.png; systemctl restart nuxel-web; fi
