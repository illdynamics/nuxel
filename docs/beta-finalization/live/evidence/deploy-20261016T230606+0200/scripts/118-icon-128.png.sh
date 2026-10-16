#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/console/icons/icon-128.png
# previous-hash: e165a24f19a16a6bf4810e7277651d332ff3252b38ccaf92d2a67dadded7c037
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' e165a24f19a16a6bf4810e7277651d332ff3252b38ccaf92d2a67dadded7c037 /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/icons/icon-128.png | grep -q e165a24f19a16a6bf4810e7277651d332ff3252b38ccaf92d2a67dadded7c037
systemctl restart nuxel-web
systemctl is-active nuxel-web
test "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/pwa/nuxel-apps/settings/index.html)" = 200 && test -s /usr/share/nuxel/pwa/nuxel-apps/clock/index.html
echo INSTALL-OK
