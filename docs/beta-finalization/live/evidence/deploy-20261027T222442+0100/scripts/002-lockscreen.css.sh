#!/bin/sh
# Lockscreen touch warning, battery guard, wider unlock band and filter-free idle rendering -> /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/css/lockscreen.css
# previous-hash: 777e1349aa774d802dff6700b82a6360fd8fb777ad73fcef34a40bf9d9c7af2e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-deploy-20261027T222442-2425280 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-deploy-20261027T222442-2425280 /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-deploy-20261027T222442-2425280 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-rollback.pre-deploy-20261027T222442-2425280; fi
test -f /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-staged
printf '%s  %s\n' 777e1349aa774d802dff6700b82a6360fd8fb777ad73fcef34a40bf9d9c7af2e /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css
sha256sum /usr/share/nuxel/pwa/nuxel-home/css/lockscreen.css | grep -q 777e1349aa774d802dff6700b82a6360fd8fb777ad73fcef34a40bf9d9c7af2e
echo INSTALL-OK
