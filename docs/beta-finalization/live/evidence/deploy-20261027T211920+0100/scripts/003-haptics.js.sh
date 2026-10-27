#!/bin/sh
# PWNAGE-30000 PWA apps, theme, haptics and widgets -> /usr/share/nuxel/pwa/nuxel-common/haptics.js (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/haptics.js
# previous-hash: 088792268134bbcf01552a3f810ecdd2bc12160268076500e355532d7420b93c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 /usr/share/nuxel/pwa/nuxel-common/haptics.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/haptics.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/haptics.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/haptics.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/haptics.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/haptics.js /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/haptics.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-rollback.pre-deploy-20261027T211920-2300900 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/haptics.js /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-rollback.pre-deploy-20261027T211920-2300900; fi
test -f /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-staged
printf '%s  %s\n' 088792268134bbcf01552a3f810ecdd2bc12160268076500e355532d7420b93c /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/haptics.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/haptics.js
sha256sum /usr/share/nuxel/pwa/nuxel-common/haptics.js | grep -q 088792268134bbcf01552a3f810ecdd2bc12160268076500e355532d7420b93c
echo INSTALL-OK
