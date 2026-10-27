#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console-wifi/index.html
# previous-hash: 5225d0c2c635af93ad31bd9242b879eaba14da37f3b3c4098630a651fb6ac85f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-rollback.pre-deploy-20261027T164310-2129080 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-rollback.pre-deploy-20261027T164310-2129080 /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-rollback.pre-deploy-20261027T164310-2129080 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-rollback.pre-deploy-20261027T164310-2129080; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-staged
printf '%s  %s\n' 5225d0c2c635af93ad31bd9242b879eaba14da37f3b3c4098630a651fb6ac85f /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console-wifi/index.html | grep -q 5225d0c2c635af93ad31bd9242b879eaba14da37f3b3c4098630a651fb6ac85f
echo INSTALL-OK
