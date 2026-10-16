#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/rootcontrol/icons/icon-128.png
# previous-hash: 47cc1d3490ddbb3d855e45e3a69c39dc9cc654eb655e5dfbabb6a6941c0f1598
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' 47cc1d3490ddbb3d855e45e3a69c39dc9cc654eb655e5dfbabb6a6941c0f1598 /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/rootcontrol/icons/icon-128.png | grep -q 47cc1d3490ddbb3d855e45e3a69c39dc9cc654eb655e5dfbabb6a6941c0f1598
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
