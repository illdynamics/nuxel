#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-home/manifest.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/manifest.json
# previous-hash: 795936660f020d6f4cbc4bbb5985627caf1d41014923d11ff064f0a04b470a83
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T163612-2117870 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T163612-2117870 /usr/share/nuxel/pwa/nuxel-home/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T163612-2117870 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261027T163612-2117870; fi
test -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged
printf '%s  %s\n' 795936660f020d6f4cbc4bbb5985627caf1d41014923d11ff064f0a04b470a83 /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | grep -q 795936660f020d6f4cbc4bbb5985627caf1d41014923d11ff064f0a04b470a83
echo INSTALL-OK
