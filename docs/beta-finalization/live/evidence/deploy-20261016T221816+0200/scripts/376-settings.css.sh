#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/settings.css
# previous-hash: 7a77a6f3b2f2a309df4f6d5b193af57d8a175818dee016b1cfa51846c07a1f18
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged
printf '%s  %s\n' 7a77a6f3b2f2a309df4f6d5b193af57d8a175818dee016b1cfa51846c07a1f18 /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css | grep -q 7a77a6f3b2f2a309df4f6d5b193af57d8a175818dee016b1cfa51846c07a1f18
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/settings.css; systemctl restart nuxel-web; fi
