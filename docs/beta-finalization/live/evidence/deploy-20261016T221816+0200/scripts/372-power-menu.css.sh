#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/settings/power-menu.css
# previous-hash: b649aac15b48d8f5a65115d0a0a79b7b67f5874c805d21561eaace56c7630fdb
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-staged
printf '%s  %s\n' b649aac15b48d8f5a65115d0a0a79b7b67f5874c805d21561eaace56c7630fdb /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css | grep -q b649aac15b48d8f5a65115d0a0a79b7b67f5874c805d21561eaace56c7630fdb
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/settings/power-menu.css; systemctl restart nuxel-web; fi
