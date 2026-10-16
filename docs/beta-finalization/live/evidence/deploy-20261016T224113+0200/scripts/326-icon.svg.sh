#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/icons/icon.svg
# previous-hash: 4c54c5f75d1c3461d3f24f3e48a242d701ffe8f50c3e97786f0e5f92f3acf3b1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg.nuxel-staged
printf '%s  %s\n' 4c54c5f75d1c3461d3f24f3e48a242d701ffe8f50c3e97786f0e5f92f3acf3b1 /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon.svg | grep -q 4c54c5f75d1c3461d3f24f3e48a242d701ffe8f50c3e97786f0e5f92f3acf3b1
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
