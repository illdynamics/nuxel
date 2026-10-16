#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/css/rootcontrol.css
# previous-hash: ad62b7acdace9ec1b9a2062755bea1e4efb66eface6d75c3459b6984ca17fc79
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css.nuxel-staged
printf '%s  %s\n' ad62b7acdace9ec1b9a2062755bea1e4efb66eface6d75c3459b6984ca17fc79 /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css | grep -q ad62b7acdace9ec1b9a2062755bea1e4efb66eface6d75c3459b6984ca17fc79
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/css/rootcontrol.css; systemctl restart nuxel-web; fi
