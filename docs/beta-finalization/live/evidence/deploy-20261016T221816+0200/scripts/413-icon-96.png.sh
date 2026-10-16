#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/weather/icons/icon-96.png
# previous-hash: 227711055267e8312b11957ed6139ebe009665a8882d1fa9ac9dc74b6ae913c3
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png.nuxel-staged
printf '%s  %s\n' 227711055267e8312b11957ed6139ebe009665a8882d1fa9ac9dc74b6ae913c3 /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png | grep -q 227711055267e8312b11957ed6139ebe009665a8882d1fa9ac9dc74b6ae913c3
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/weather/icons/icon-96.png; systemctl restart nuxel-web; fi
