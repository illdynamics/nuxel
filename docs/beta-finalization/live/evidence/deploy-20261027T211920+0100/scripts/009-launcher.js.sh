#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-home/js/launcher.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/launcher.js
# previous-hash: d6ced9efa9794406a90340cc47eb800c932ef09f4568aca6650e79ec5ddf4e68
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-home/js/launcher.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/launcher.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/launcher.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged
printf '%s  %s\n' d6ced9efa9794406a90340cc47eb800c932ef09f4568aca6650e79ec5ddf4e68 /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/launcher.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/launcher.js | grep -q d6ced9efa9794406a90340cc47eb800c932ef09f4568aca6650e79ec5ddf4e68
echo INSTALL-OK
