#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/weather/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/index.html
# previous-hash: c8dc6074aade4f76aaf5765bec44ff0b0ecd16eeb01e1599870a179043de1330
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/index.html /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-staged
printf '%s  %s\n' c8dc6074aade4f76aaf5765bec44ff0b0ecd16eeb01e1599870a179043de1330 /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/index.html | grep -q c8dc6074aade4f76aaf5765bec44ff0b0ecd16eeb01e1599870a179043de1330
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/weather/index.html; systemctl restart nuxel-web; fi
