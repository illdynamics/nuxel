#!/bin/sh
# Crispy Doom touch launcher and bridge route -> /usr/lib/nuxel/nuxel-doom-launcher (service: nuxel-http-bridge, risk: medium)
# staged source: tools/s10plus/a33/nuxel-doom-launcher
# previous-hash: 95d937ebae70c63ee1ca8e96283133d6fe92c913a0ea684bd70f018256be455d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-doom-launcher.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-doom-launcher.nuxel-rollback.pre-deploy-20261104T112828-3208175 /usr/lib/nuxel/nuxel-doom-launcher; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-doom-launcher ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-doom-launcher | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-doom-launcher)"
if [ -e /usr/lib/nuxel/nuxel-doom-launcher ] && [ ! -e /usr/lib/nuxel/nuxel-doom-launcher.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-doom-launcher /usr/lib/nuxel/nuxel-doom-launcher.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-doom-launcher ] && [ ! -e /usr/lib/nuxel/nuxel-doom-launcher.nuxel-rollback.pre-deploy-20261104T112828-3208175 ]; then cp -a /usr/lib/nuxel/nuxel-doom-launcher /usr/lib/nuxel/nuxel-doom-launcher.nuxel-rollback.pre-deploy-20261104T112828-3208175; fi
test -f /usr/lib/nuxel/nuxel-doom-launcher.nuxel-staged
printf '%s  %s\n' 95d937ebae70c63ee1ca8e96283133d6fe92c913a0ea684bd70f018256be455d /usr/lib/nuxel/nuxel-doom-launcher.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-doom-launcher.nuxel-staged /usr/lib/nuxel/nuxel-doom-launcher
sha256sum /usr/lib/nuxel/nuxel-doom-launcher | grep -q 95d937ebae70c63ee1ca8e96283133d6fe92c913a0ea684bd70f018256be455d
echo INSTALL-OK
