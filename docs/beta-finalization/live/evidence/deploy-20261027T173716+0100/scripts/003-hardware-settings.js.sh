#!/bin/sh
# Settings PWA (Bluetooth/Displays/Audio pages) + Home QS + shared bridge client -> /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js (service: nuxel-http-bridge, risk: low)
# staged source: pwa/nuxel-apps/settings/hardware-settings.js
# previous-hash: 028ea9d34573452ac28700a2a70d98a06a1e930b7d7c20615d00a85def7bbc2f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T173716-2158850 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T173716-2158850 /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T173716-2158850 ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-rollback.pre-deploy-20261027T173716-2158850; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged
printf '%s  %s\n' 028ea9d34573452ac28700a2a70d98a06a1e930b7d7c20615d00a85def7bbc2f /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/settings/hardware-settings.js | grep -q 028ea9d34573452ac28700a2a70d98a06a1e930b7d7c20615d00a85def7bbc2f
echo INSTALL-OK
