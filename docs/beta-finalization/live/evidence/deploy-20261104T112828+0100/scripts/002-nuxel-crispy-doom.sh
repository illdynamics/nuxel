#!/bin/sh
# Crispy Doom touch launcher and bridge route -> /usr/lib/nuxel/nuxel-crispy-doom (service: nuxel-http-bridge, risk: medium)
# staged source: tools/s10plus/a33/nuxel-crispy-doom
# previous-hash: 29d811b73e134688c89d84501fbbe2eba351aaf5e46e11e19fd377f81aaad6ae
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-crispy-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-crispy-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175 /usr/lib/nuxel/nuxel-crispy-doom; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-crispy-doom ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-crispy-doom | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-crispy-doom)"
if [ -e /usr/lib/nuxel/nuxel-crispy-doom ] && [ ! -e /usr/lib/nuxel/nuxel-crispy-doom.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-crispy-doom /usr/lib/nuxel/nuxel-crispy-doom.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-crispy-doom ] && [ ! -e /usr/lib/nuxel/nuxel-crispy-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-crispy-doom /usr/lib/nuxel/nuxel-crispy-doom.nuxel-rollback.pre-deploy-20261104T112828-3208175; fi
test -f /usr/lib/nuxel/nuxel-crispy-doom.nuxel-staged
printf '%s  %s\n' 29d811b73e134688c89d84501fbbe2eba351aaf5e46e11e19fd377f81aaad6ae /usr/lib/nuxel/nuxel-crispy-doom.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-crispy-doom.nuxel-staged /usr/lib/nuxel/nuxel-crispy-doom
sha256sum /usr/lib/nuxel/nuxel-crispy-doom | grep -q 29d811b73e134688c89d84501fbbe2eba351aaf5e46e11e19fd377f81aaad6ae
echo INSTALL-OK
