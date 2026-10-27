#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/manifest.json
# previous-hash: de95552f766c6a62125f41d2f74c4520a922b1d1365d6cd9087cca4c20825835
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-rollback.pre-deploy-20261027T182142-2202036; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-staged
printf '%s  %s\n' de95552f766c6a62125f41d2f74c4520a922b1d1365d6cd9087cca4c20825835 /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/manifest.json | grep -q de95552f766c6a62125f41d2f74c4520a922b1d1365d6cd9087cca4c20825835
echo INSTALL-OK
