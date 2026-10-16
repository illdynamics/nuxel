#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/status-bar.css
# previous-hash: 1213cfc3e2eabb93d35a4070a4fdd09b83facd4a71a5af7831af1c3bef42c351
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged
printf '%s  %s\n' 1213cfc3e2eabb93d35a4070a4fdd09b83facd4a71a5af7831af1c3bef42c351 /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css | grep -q 1213cfc3e2eabb93d35a4070a4fdd09b83facd4a71a5af7831af1c3bef42c351
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/css/status-bar.css; systemctl restart nuxel-web; fi
