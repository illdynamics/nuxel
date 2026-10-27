#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-home/manifest.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/manifest.json
# previous-hash: 419f61d5c2c1ac5fc7b962809d3e2cace9e2b3fa9f3d4e3434f9e5ccd48b5867
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T181522-2198480 /usr/share/nuxel/pwa/nuxel-home/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T181522-2198480; fi
test -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged
printf '%s  %s\n' 419f61d5c2c1ac5fc7b962809d3e2cace9e2b3fa9f3d4e3434f9e5ccd48b5867 /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | grep -q 419f61d5c2c1ac5fc7b962809d3e2cace9e2b3fa9f3d4e3434f9e5ccd48b5867
echo INSTALL-OK
