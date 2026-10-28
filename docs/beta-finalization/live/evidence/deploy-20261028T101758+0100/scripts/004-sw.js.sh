#!/bin/sh
# Disable DOM keyboard fallback when Stevia provider is present; bump PWA cache -> /usr/share/nuxel/pwa/nuxel-home/sw.js (service: nuxel-wayland, risk: low)
# staged source: pwa/nuxel-home/sw.js
# previous-hash: 1ce1f82cd471f4a50823177d15a89fd863299d2481b8b9255fd12fd90f7692d1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261028T101758-2799662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261028T101758-2799662 /usr/share/nuxel/pwa/nuxel-home/sw.js; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-home/sw.js)"
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-home/sw.js ] && [ ! -e /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261028T101758-2799662 ]; then cp -a /usr/share/nuxel/pwa/nuxel-home/sw.js /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-rollback.pre-deploy-20261028T101758-2799662; fi
test -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged
printf '%s  %s\n' 1ce1f82cd471f4a50823177d15a89fd863299d2481b8b9255fd12fd90f7692d1 /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-home/sw.js.nuxel-staged /usr/share/nuxel/pwa/nuxel-home/sw.js
sha256sum /usr/share/nuxel/pwa/nuxel-home/sw.js | grep -q 1ce1f82cd471f4a50823177d15a89fd863299d2481b8b9255fd12fd90f7692d1
echo INSTALL-OK
