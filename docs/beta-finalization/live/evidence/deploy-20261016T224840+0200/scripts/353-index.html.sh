#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/index.html
# previous-hash: a9cee317b995a9acb3de89807888add6786b1b2efe656ffb740f5bd3e4749c08
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html.nuxel-staged
printf '%s  %s\n' a9cee317b995a9acb3de89807888add6786b1b2efe656ffb740f5bd3e4749c08 /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/index.html | grep -q a9cee317b995a9acb3de89807888add6786b1b2efe656ffb740f5bd3e4749c08
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
