#!/bin/sh
# v0.7.1-beta PWA version pins and launcher cache namespace -> /usr/share/nuxel/pwa/nuxel-home/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/manifest.json
# previous-hash: 30fd507f98491710f8a429168a2e72d2c933b693c0dfe8dd4e7d65d8d9ad8bc2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T214530-2399261 /usr/share/nuxel/pwa/nuxel-home/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged
printf '%s  %s\n' 30fd507f98491710f8a429168a2e72d2c933b693c0dfe8dd4e7d65d8d9ad8bc2 /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | grep -q 30fd507f98491710f8a429168a2e72d2c933b693c0dfe8dd4e7d65d8d9ad8bc2
echo INSTALL-OK
