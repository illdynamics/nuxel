#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/settings-store.js
# previous-hash: 383e068515aba43da0026d6dc1e0250f34cd87f8f1d7014db2c7831cd18c9c1d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged
printf '%s  %s\n' 383e068515aba43da0026d6dc1e0250f34cd87f8f1d7014db2c7831cd18c9c1d /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/settings-store.js | grep -q 383e068515aba43da0026d6dc1e0250f34cd87f8f1d7014db2c7831cd18c9c1d
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-home/index.html)" = 200
echo INSTALL-OK
