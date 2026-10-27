#!/bin/sh
# Settings PWA (Bluetooth/Displays/Audio pages) + Home QS + shared bridge client -> /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/settings/hardware-settings.js
# previous-hash: 9fd85d2bbfaf157a5d116fcb8700ce78a21bf22c554667dc12c4be871054b430
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T172231-2153662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T172231-2153662 /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T172231-2153662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T172231-2153662; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged
printf '%s  %s\n' 9fd85d2bbfaf157a5d116fcb8700ce78a21bf22c554667dc12c4be871054b430 /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js | grep -q 9fd85d2bbfaf157a5d116fcb8700ce78a21bf22c554667dc12c4be871054b430
echo INSTALL-OK
