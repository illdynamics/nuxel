#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/files/icons/icon-128.png
# previous-hash: f4fa1746795202f29de7114c36ed63db724a2157a954a8148260f0ab3da1effb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png.nuxel-staged
printf '%s  %s\n' f4fa1746795202f29de7114c36ed63db724a2157a954a8148260f0ab3da1effb /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png
sha256sum /usr/share/nuxel/pwa/nuxel-apps/files/icons/icon-128.png | grep -q f4fa1746795202f29de7114c36ed63db724a2157a954a8148260f0ab3da1effb
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
