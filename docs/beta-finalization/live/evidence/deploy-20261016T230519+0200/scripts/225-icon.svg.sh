#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/media/icons/icon.svg
# previous-hash: 55c3b12259372417cb784e76c0d098f57dc0d215a37c07fdf42c0f60780a5b3b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg.nuxel-staged
printf '%s  %s\n' 55c3b12259372417cb784e76c0d098f57dc0d215a37c07fdf42c0f60780a5b3b /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/media/icons/icon.svg | grep -q 55c3b12259372417cb784e76c0d098f57dc0d215a37c07fdf42c0f60780a5b3b
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
