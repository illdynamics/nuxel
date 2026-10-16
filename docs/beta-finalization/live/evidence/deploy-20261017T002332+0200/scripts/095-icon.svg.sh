#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/cleanup/icons/icon.svg
# previous-hash: 72e77a53fe528e90f7a4736a384afd9aefe106bd08e5866fa3150c191954a3d4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg.nuxel-staged
printf '%s  %s\n' 72e77a53fe528e90f7a4736a384afd9aefe106bd08e5866fa3150c191954a3d4 /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg
sha256sum /usr/share/nuxel/pwa/nuxel-apps/cleanup/icons/icon.svg | grep -q 72e77a53fe528e90f7a4736a384afd9aefe106bd08e5866fa3150c191954a3d4
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
