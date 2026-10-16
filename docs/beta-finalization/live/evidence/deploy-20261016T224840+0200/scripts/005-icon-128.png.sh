#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/authenticator/icons/icon-128.png
# previous-hash: cf6c57ae9b0a5666f7aa5553b18b9af383ae0b6087edf8b4e8bd6f6df6b4c748
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' cf6c57ae9b0a5666f7aa5553b18b9af383ae0b6087edf8b4e8bd6f6df6b4c748 /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/authenticator/icons/icon-128.png | grep -q cf6c57ae9b0a5666f7aa5553b18b9af383ae0b6087edf8b4e8bd6f6df6b4c748
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
