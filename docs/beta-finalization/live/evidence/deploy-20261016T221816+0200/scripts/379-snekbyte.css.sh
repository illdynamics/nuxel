#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/css/snekbyte.css
# previous-hash: 57ea06d1368068d84d222ec3e955b8f860e3886d3005c4e7ad93a65aeebc078e
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css.nuxel-staged
printf '%s  %s\n' 57ea06d1368068d84d222ec3e955b8f860e3886d3005c4e7ad93a65aeebc078e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css | grep -q 57ea06d1368068d84d222ec3e955b8f860e3886d3005c4e7ad93a65aeebc078e
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/css/snekbyte.css; systemctl restart nuxel-web; fi
