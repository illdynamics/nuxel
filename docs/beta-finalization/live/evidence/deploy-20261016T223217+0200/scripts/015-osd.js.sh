#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/osd.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/osd.js
# previous-hash: f1b5c4e99dd6d5ada3ff8de2bd99ffed3ef26f65de8f1af02dea07ca82fef794
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/osd.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/osd.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/osd.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/osd.js /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged
printf '%s  %s\n' f1b5c4e99dd6d5ada3ff8de2bd99ffed3ef26f65de8f1af02dea07ca82fef794 /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/osd.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/osd.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/osd.js | grep -q f1b5c4e99dd6d5ada3ff8de2bd99ffed3ef26f65de8f1af02dea07ca82fef794
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
