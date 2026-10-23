#!/bin/sh
# launcher (Nuxel Home PWA) -> /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/status-bar.js
# previous-hash: 5148a909c318619d12a16dd2567dfa50460e235fab9bf2e4b0cfefc6e7ccab37
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js; systemctl restart nuxel-web; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-rollback; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged
printf '%s  %s\n' 5148a909c318619d12a16dd2567dfa50460e235fab9bf2e4b0cfefc6e7ccab37 /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js | grep -q 5148a909c318619d12a16dd2567dfa50460e235fab9bf2e4b0cfefc6e7ccab37
systemctl restart nuxel-web
systemctl is-active nuxel-web
echo INSTALL-OK
