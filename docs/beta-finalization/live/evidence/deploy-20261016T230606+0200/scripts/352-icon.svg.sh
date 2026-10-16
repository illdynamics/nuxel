#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/snekbyte/icons/icon.svg
# previous-hash: d31e4d755afd4901859c22a45d24b1508fe2ef8085ecf2d894ce156cfefa2f0c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg.nuxel-staged
printf '%s  %s\n' d31e4d755afd4901859c22a45d24b1508fe2ef8085ecf2d894ce156cfefa2f0c /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/snekbyte/icons/icon.svg | grep -q d31e4d755afd4901859c22a45d24b1508fe2ef8085ecf2d894ce156cfefa2f0c
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
