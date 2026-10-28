#!/bin/sh
# Lockscreen touch warning, battery guard, wider unlock band and filter-free idle rendering -> /usr/share/nuxel/pwa/nuxel-home/index.html (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/index.html
# previous-hash: e82bfd4584cd9bf93b0b325484955c93cb9b15dca21850ffa5b3d8ccd34d622d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T222439-2425125 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T222439-2425125 /usr/share/nuxel/pwa/nuxel-home/index.html; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/index.html)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/index.html ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T222439-2425125 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/index.html /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-rollback.pre-deploy-20261027T222439-2425125; fi
test -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged
printf '%s  %s\n' e82bfd4584cd9bf93b0b325484955c93cb9b15dca21850ffa5b3d8ccd34d622d /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/index.html.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/index.html
sha256sum /usr/share/nuxel/pwa/nuxel-home/index.html | grep -q e82bfd4584cd9bf93b0b325484955c93cb9b15dca21850ffa5b3d8ccd34d622d
echo INSTALL-OK
