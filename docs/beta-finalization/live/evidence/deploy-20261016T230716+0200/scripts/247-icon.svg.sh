#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/notes/icons/icon.svg
# previous-hash: f778f8c64b53f3f2fdb4a9c15b09511a5d0f013a4227a7f1d9ad0ef769e9916c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg.nuxel-staged
printf '%s  %s\n' f778f8c64b53f3f2fdb4a9c15b09511a5d0f013a4227a7f1d9ad0ef769e9916c /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/notes/icons/icon.svg | grep -q f778f8c64b53f3f2fdb4a9c15b09511a5d0f013a4227a7f1d9ad0ef769e9916c
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
