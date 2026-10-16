#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calendar/icons/icon-128.png
# previous-hash: 8ede5f3ce48b354a5e02a30ebcb970648c6aa28f61ecb24de5ef944664e803db
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' 8ede5f3ce48b354a5e02a30ebcb970648c6aa28f61ecb24de5ef944664e803db /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png | grep -q 8ede5f3ce48b354a5e02a30ebcb970648c6aa28f61ecb24de5ef944664e803db
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calendar/icons/icon-128.png; systemctl restart nuxel-web; fi
