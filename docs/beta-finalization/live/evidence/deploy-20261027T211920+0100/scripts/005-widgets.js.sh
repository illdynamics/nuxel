#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-home/js/widgets.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-home/js/widgets.js
# previous-hash: ded8666538126ea5e93a45009f62185ab116598254f1e3a894b58ffc9c34d9a0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-home/js/widgets.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/widgets.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/js/widgets.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/js/widgets.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/widgets.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/widgets.js /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/js/widgets.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/js/widgets.js /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-staged
printf '%s  %s\n' ded8666538126ea5e93a45009f62185ab116598254f1e3a894b58ffc9c34d9a0 /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/js/widgets.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/js/widgets.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/widgets.js | grep -q ded8666538126ea5e93a45009f62185ab116598254f1e3a894b58ffc9c34d9a0
echo INSTALL-OK
