#!/bin/sh
# launcher (Nuxel Home PWA) -> /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/colour-test.html
# previous-hash: 1a1f15416829c1c8194ca6c638924156420104ac11095dd94458903b6dba574d
set -eu
mkdir -p "$(dirname /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html)"
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback; fi
test -f /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html.nuxel-staged
printf '%s  %s\n' 1a1f15416829c1c8194ca6c638924156420104ac11095dd94458903b6dba574d /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html.nuxel-staged /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html
sha256sum /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html | grep -q 1a1f15416829c1c8194ca6c638924156420104ac11095dd94458903b6dba574d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
# rollback (run only if the health check above failed)
if [ -e /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback ]; then cp -a /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html.nuxel-rollback /home/nuxel/nuxel/pwa/nuxel-home/colour-test.html; systemctl restart nuxel-web; fi
