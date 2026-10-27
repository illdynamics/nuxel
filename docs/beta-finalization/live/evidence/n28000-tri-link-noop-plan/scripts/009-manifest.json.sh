#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console/manifest.json
# previous-hash: 11eade2b546f54d141dd42d0574e8f2f3c70300299f2d2fafc8c5ed475269211
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-rollback.pre-deploy-20261027T164331-2129532 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-rollback.pre-deploy-20261027T164331-2129532 /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-rollback.pre-deploy-20261027T164331-2129532 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-rollback.pre-deploy-20261027T164331-2129532; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-staged
printf '%s  %s\n' 11eade2b546f54d141dd42d0574e8f2f3c70300299f2d2fafc8c5ed475269211 /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/manifest.json | grep -q 11eade2b546f54d141dd42d0574e8f2f3c70300299f2d2fafc8c5ed475269211
echo INSTALL-OK
