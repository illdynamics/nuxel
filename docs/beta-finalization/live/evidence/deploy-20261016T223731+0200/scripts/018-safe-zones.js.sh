#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/safe-zones.js
# previous-hash: 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged
printf '%s  %s\n' 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/safe-zones.js | grep -q 0ef0c91a45b599881f4eea26fca2c08ffdde806ec52dd48472c042ecb5806a0f
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
