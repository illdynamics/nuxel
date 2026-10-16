#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/css/style.css (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/css/style.css
# previous-hash: 39ff68fd920d55cc68733a0f1f1ef0ada2433d6c95946cded95aa084ac156eb4
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/css/style.css)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/css/style.css ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/css/style.css /home/nuxel/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged
printf '%s  %s\n' 39ff68fd920d55cc68733a0f1f1ef0ada2433d6c95946cded95aa084ac156eb4 /home/nuxel/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/css/style.css.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/css/style.css
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/css/style.css | grep -q 39ff68fd920d55cc68733a0f1f1ef0ada2433d6c95946cded95aa084ac156eb4
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/css/style.css.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/css/style.css; systemctl restart nuxel-web; fi
