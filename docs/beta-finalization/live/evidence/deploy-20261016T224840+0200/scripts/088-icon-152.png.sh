#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/icons/icon-152.png
# previous-hash: 060310e1eca4c323167e8cfcd228cfc98ddf6612d58c188f4a33bfc8c0e8a694
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png.nuxel-staged
printf '%s  %s\n' 060310e1eca4c323167e8cfcd228cfc98ddf6612d58c188f4a33bfc8c0e8a694 /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon-152.png | grep -q 060310e1eca4c323167e8cfcd228cfc98ddf6612d58c188f4a33bfc8c0e8a694
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
