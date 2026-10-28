#!/bin/sh
# Lockscreen touch warning, battery guard, wider unlock band and filter-free idle rendering -> /usr/share/nuxel/pwa/nuxel-home/sw.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/sw.js
# previous-hash: 6a416c4593c9bd240f461bc89b8036fb1b3426bbae51053ef92a854f0f4e6dad
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T222442-2425280 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T222442-2425280 /usr/share/nuxel/pwa/nuxel-home/sw.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T222442-2425280 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261027T222442-2425280; fi
test -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged
printf '%s  %s\n' 6a416c4593c9bd240f461bc89b8036fb1b3426bbae51053ef92a854f0f4e6dad /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | grep -q 6a416c4593c9bd240f461bc89b8036fb1b3426bbae51053ef92a854f0f4e6dad
echo INSTALL-OK
