#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-common/theme.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/theme.js
# previous-hash: f8d48ee1368e3c7a2b814c6befe0a79847b03dd108c273013713aa04a9069be7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 /usr/share/nuxel/pwa/nuxel-common/theme.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/theme.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/theme.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/theme.js /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/theme.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-rollback.pre-deploy-20261027T213506-2390765 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/theme.js /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-rollback.pre-deploy-20261027T213506-2390765; fi
test -f /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-staged
printf '%s  %s\n' f8d48ee1368e3c7a2b814c6befe0a79847b03dd108c273013713aa04a9069be7 /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/theme.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/theme.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/theme.js | grep -q f8d48ee1368e3c7a2b814c6befe0a79847b03dd108c273013713aa04a9069be7
echo INSTALL-OK
