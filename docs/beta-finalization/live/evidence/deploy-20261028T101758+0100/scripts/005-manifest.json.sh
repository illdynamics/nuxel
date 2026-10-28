#!/bin/sh
# Disable DOM keyboard fallback when Stevia provider is present; bump PWA cache -> /usr/share/nuxel/pwa/nuxel-home/manifest.json (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/manifest.json
# previous-hash: ecabebc41b976aa69d08491d18eaff4dd150346537f9abd5e7bf0dfdc6690f0b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261028T101758-2799662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261028T101758-2799662 /usr/share/nuxel/pwa/nuxel-home/manifest.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/manifest.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/manifest.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261028T101758-2799662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/manifest.json /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-rollback.pre-deploy-20261028T101758-2799662; fi
test -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged
printf '%s  %s\n' ecabebc41b976aa69d08491d18eaff4dd150346537f9abd5e7bf0dfdc6690f0b /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/manifest.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/manifest.json
sha256sum /usr/share/nuxel/pwa/nuxel-home/manifest.json | grep -q ecabebc41b976aa69d08491d18eaff4dd150346537f9abd5e7bf0dfdc6690f0b
echo INSTALL-OK
