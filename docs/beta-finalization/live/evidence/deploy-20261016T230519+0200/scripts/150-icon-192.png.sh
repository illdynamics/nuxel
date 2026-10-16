#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/downloader/icons/icon-192.png
# previous-hash: ce7d1770d62dadb340ee9d4e6f6496e65515112cffd956c22f636360a74c4a25
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png.nuxel-staged
printf '%s  %s\n' ce7d1770d62dadb340ee9d4e6f6496e65515112cffd956c22f636360a74c4a25 /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/downloader/icons/icon-192.png | grep -q ce7d1770d62dadb340ee9d4e6f6496e65515112cffd956c22f636360a74c4a25
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
