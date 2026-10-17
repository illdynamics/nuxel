#!/bin/sh
# PWA application suite (pwa/nuxel-apps/**) -> /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-apps/mail/sw.js
# previous-hash: b2454febd6a0652cae391dff1492a67a24be28ecb5b3d3b8ffb0d3c94fbd8d4e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js.nuxel-staged
printf '%s  %s\n' b2454febd6a0652cae391dff1492a67a24be28ecb5b3d3b8ffb0d3c94fbd8d4e /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-apps/mail/sw.js | grep -q b2454febd6a0652cae391dff1492a67a24be28ecb5b3d3b8ffb0d3c94fbd8d4e
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
