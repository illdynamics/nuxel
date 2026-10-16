#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/icons/icon-152.png
# previous-hash: 5c85d250f3e6087e09850b052e8f440645774d4d4ccdf43c284a94cd634ab666
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png.nuxel-staged
printf '%s  %s\n' 5c85d250f3e6087e09850b052e8f440645774d4d4ccdf43c284a94cd634ab666 /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon-152.png | grep -q 5c85d250f3e6087e09850b052e8f440645774d4d4ccdf43c284a94cd634ab666
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
