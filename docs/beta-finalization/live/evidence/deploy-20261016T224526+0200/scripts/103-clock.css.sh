#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/clock/css/clock.css
# previous-hash: b4e0bc68e73a04545a543eb3f96014aa86a6b4e65fed3aa9579a0e0f8356bd13
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-staged
printf '%s  %s\n' b4e0bc68e73a04545a543eb3f96014aa86a6b4e65fed3aa9579a0e0f8356bd13 /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/clock/css/clock.css | grep -q b4e0bc68e73a04545a543eb3f96014aa86a6b4e65fed3aa9579a0e0f8356bd13
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
