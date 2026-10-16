#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/launcher.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/launcher.css
# previous-hash: dde7b3d2d71b082123efe73675669ce560c3a284a5b8c6c96bd13327c53659a6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/launcher.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/launcher.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/launcher.css ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/launcher.css /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged
printf '%s  %s\n' dde7b3d2d71b082123efe73675669ce560c3a284a5b8c6c96bd13327c53659a6 /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/launcher.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/launcher.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/launcher.css | grep -q dde7b3d2d71b082123efe73675669ce560c3a284a5b8c6c96bd13327c53659a6
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
