#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/bridge.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/bridge.js
# previous-hash: bbfc2823118c6f83e99549c348347fd17da20e60fb317de6962c1b0ab513497b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/bridge.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bridge.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/bridge.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/bridge.js /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged
printf '%s  %s\n' bbfc2823118c6f83e99549c348347fd17da20e60fb317de6962c1b0ab513497b /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/bridge.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/bridge.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/bridge.js | grep -q bbfc2823118c6f83e99549c348347fd17da20e60fb317de6962c1b0ab513497b
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
