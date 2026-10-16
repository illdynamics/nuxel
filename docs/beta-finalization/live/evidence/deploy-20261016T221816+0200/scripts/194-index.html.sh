#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/index.html
# previous-hash: d5f4ce8e741ff8f4480200666216045cce8ac167ef9e6a703e42342a3caf1c72
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html.nuxel-staged
printf '%s  %s\n' d5f4ce8e741ff8f4480200666216045cce8ac167ef9e6a703e42342a3caf1c72 /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html | grep -q d5f4ce8e741ff8f4480200666216045cce8ac167ef9e6a703e42342a3caf1c72
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/index.html; systemctl restart nuxel-web; fi
