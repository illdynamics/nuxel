#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/maps/index.html (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/maps/index.html
# previous-hash: 152d58179152631c4915ca1cc3d85f0beb7208c6b56a3a36b3bae719b9718a4e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/maps/index.html; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/index.html /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-staged
printf '%s  %s\n' 152d58179152631c4915ca1cc3d85f0beb7208c6b56a3a36b3bae719b9718a4e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/index.html | grep -q 152d58179152631c4915ca1cc3d85f0beb7208c6b56a3a36b3bae719b9718a4e
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
