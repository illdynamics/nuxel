#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/status-bar.js
# previous-hash: 7a2f02eacff1fe904c73ad631d1882406c4a9c9d4512e9cfceee6f4ff6606723
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged
printf '%s  %s\n' 7a2f02eacff1fe904c73ad631d1882406c4a9c9d4512e9cfceee6f4ff6606723 /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js | grep -q 7a2f02eacff1fe904c73ad631d1882406c4a9c9d4512e9cfceee6f4ff6606723
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
