#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/maps/index.html (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/maps/index.html
# previous-hash: 03e5d84f54f13dcfbb18bef9b444689fc42c8b83856490136ecefe7040f64ddd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback.pre-deploy-20261027T182142-2202036 /usr/share/nuxel/pwa/nuxel-apps/maps/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/maps/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/index.html /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/maps/index.html /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-rollback.pre-deploy-20261027T182142-2202036; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-staged
printf '%s  %s\n' 03e5d84f54f13dcfbb18bef9b444689fc42c8b83856490136ecefe7040f64ddd /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/maps/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/maps/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/maps/index.html | grep -q 03e5d84f54f13dcfbb18bef9b444689fc42c8b83856490136ecefe7040f64ddd
echo INSTALL-OK
