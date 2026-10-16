#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/css/style.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/style.css
# previous-hash: 39ff68fd920d55cc68733a0f1f1ef0ada2433d6c95946cded95aa084ac156eb4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/css/style.css; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/style.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/style.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/style.css /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged
printf '%s  %s\n' 39ff68fd920d55cc68733a0f1f1ef0ada2433d6c95946cded95aa084ac156eb4 /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/style.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/style.css | grep -q 39ff68fd920d55cc68733a0f1f1ef0ada2433d6c95946cded95aa084ac156eb4
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
