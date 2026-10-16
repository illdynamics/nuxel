#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/icons/icon-128.png
# previous-hash: bc02068cc6bea9270578688032b83372c5b81196345a3e54970dad347d2347bb
set -eu
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' bc02068cc6bea9270578688032b83372c5b81196345a3e54970dad347d2347bb /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png | grep -q bc02068cc6bea9270578688032b83372c5b81196345a3e54970dad347d2347bb
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-128.png; systemctl restart nuxel-web; fi
