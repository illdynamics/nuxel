#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/status-bar.css
# previous-hash: 1213cfc3e2eabb93d35a4070a4fdd09b83facd4a71a5af7831af1c3bef42c351
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged
printf '%s  %s\n' 1213cfc3e2eabb93d35a4070a4fdd09b83facd4a71a5af7831af1c3bef42c351 /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css | grep -q 1213cfc3e2eabb93d35a4070a4fdd09b83facd4a71a5af7831af1c3bef42c351
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
