#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calculator/css/calculator.css
# previous-hash: e2b14f7f31c3384dab8a6885bd7dca7badf9982c552f893ce0447d2970509ff5
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-staged
printf '%s  %s\n' e2b14f7f31c3384dab8a6885bd7dca7badf9982c552f893ce0447d2970509ff5 /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css | grep -q e2b14f7f31c3384dab8a6885bd7dca7badf9982c552f893ce0447d2970509ff5
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calculator/css/calculator.css; systemctl restart nuxel-web; fi
