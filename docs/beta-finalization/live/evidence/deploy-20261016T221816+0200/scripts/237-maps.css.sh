#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/maps/css/maps.css
# previous-hash: 2a2ffe347766a678d177166bd53f2bc4e6cc668c19d67700211d44c58f93b79d
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged
printf '%s  %s\n' 2a2ffe347766a678d177166bd53f2bc4e6cc668c19d67700211d44c58f93b79d /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css | grep -q 2a2ffe347766a678d177166bd53f2bc4e6cc668c19d67700211d44c58f93b79d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/maps/css/maps.css; systemctl restart nuxel-web; fi
