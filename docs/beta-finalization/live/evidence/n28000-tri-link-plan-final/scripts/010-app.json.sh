#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-apps/console/app.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/console/app.json
# previous-hash: dcb31a1503c9ec12ecf84c1542e5bbe2bdb5fd750b2ec3cacb9a41744679b9ba
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-rollback.pre-deploy-20261027T163854-2125055 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-rollback.pre-deploy-20261027T163854-2125055 /usr/share/nuxel/pwa/nuxel-apps/console/app.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/app.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/app.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/app.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/app.json /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/app.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-rollback.pre-deploy-20261027T163854-2125055 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/app.json /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-rollback.pre-deploy-20261027T163854-2125055; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-staged
printf '%s  %s\n' dcb31a1503c9ec12ecf84c1542e5bbe2bdb5fd750b2ec3cacb9a41744679b9ba /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/app.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/app.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/app.json | grep -q dcb31a1503c9ec12ecf84c1542e5bbe2bdb5fd750b2ec3cacb9a41744679b9ba
echo INSTALL-OK
