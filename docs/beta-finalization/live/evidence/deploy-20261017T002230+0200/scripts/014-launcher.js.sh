#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/launcher.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/launcher.js
# previous-hash: 3dc737d867a2ad31a10c4a1f8a472b77e78b76a7065a6b34b88be3dd88c91346
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/launcher.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/launcher.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/launcher.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/launcher.js /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged
printf '%s  %s\n' 3dc737d867a2ad31a10c4a1f8a472b77e78b76a7065a6b34b88be3dd88c91346 /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/launcher.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/launcher.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/launcher.js | grep -q 3dc737d867a2ad31a10c4a1f8a472b77e78b76a7065a6b34b88be3dd88c91346
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
