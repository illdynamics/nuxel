#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-apps/console/console.css (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-apps/console/console.css
# previous-hash: 4f985e8a57dee42278993e469bd38ac3b6cb47a122fd3bd7e4fe6e8937e5987a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-rollback.pre-v070-release /usr/share/nuxel/pwa/nuxel-apps/console/console.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/console.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/console/console.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/console.css /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-apps/console/console.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-rollback.pre-v070-release ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/console/console.css /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-rollback.pre-v070-release; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-staged
printf '%s  %s\n' 4f985e8a57dee42278993e469bd38ac3b6cb47a122fd3bd7e4fe6e8937e5987a /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/console/console.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/console/console.css
sha256sum /usr/share/nuxel/pwa/nuxel-apps/console/console.css | grep -q 4f985e8a57dee42278993e469bd38ac3b6cb47a122fd3bd7e4fe6e8937e5987a
echo INSTALL-OK
