#!/bin/sh
# launcher remainder + shared PWA runtime (pwa/nuxel-common) -> /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/icons/icon-144.png
# previous-hash: 99a73c616072eb70f30e2b0ab1704b6eb364ecd199933aa85caecdbf4ee03672
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png.nuxel-staged
printf '%s  %s\n' 99a73c616072eb70f30e2b0ab1704b6eb364ecd199933aa85caecdbf4ee03672 /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/icons/icon-144.png | grep -q 99a73c616072eb70f30e2b0ab1704b6eb364ecd199933aa85caecdbf4ee03672
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-common/bridge.js)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
echo INSTALL-OK
