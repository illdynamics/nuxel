#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/calculator/index.html
# previous-hash: 3f06ff2c1a4c59934154a5eab3b96e912c2a8dbacdbad81df4e92e1442714156
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html.nuxel-staged
printf '%s  %s\n' 3f06ff2c1a4c59934154a5eab3b96e912c2a8dbacdbad81df4e92e1442714156 /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/calculator/index.html | grep -q 3f06ff2c1a4c59934154a5eab3b96e912c2a8dbacdbad81df4e92e1442714156
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
