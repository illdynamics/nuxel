#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/js/privilege-model.js
# previous-hash: 41fd1e96b171a19f5c41c2ee74ef3419b2560513bb2943430941b70843f1206e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js.nuxel-staged
printf '%s  %s\n' 41fd1e96b171a19f5c41c2ee74ef3419b2560513bb2943430941b70843f1206e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/js/privilege-model.js | grep -q 41fd1e96b171a19f5c41c2ee74ef3419b2560513bb2943430941b70843f1206e
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
