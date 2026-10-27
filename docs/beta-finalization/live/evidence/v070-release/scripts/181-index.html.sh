#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console/index.html (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console/index.html
# previous-hash: b7fc76d120ddb21535f616f82c761fa142cd3b662757e8d953f2fac58b96f8dc
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/console/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/index.html /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/index.html /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-staged
printf '%s  %s\n' b7fc76d120ddb21535f616f82c761fa142cd3b662757e8d953f2fac58b96f8dc /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/index.html | grep -q b7fc76d120ddb21535f616f82c761fa142cd3b662757e8d953f2fac58b96f8dc
echo INSTALL-OK
