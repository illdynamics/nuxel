#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /usr/lib/nuxel/nuxel-preload-cinema (service: None, risk: low)
# staged source: services/nuxel-preload-cinema/nuxel-preload-cinema
# previous-hash: f4c74d3d3d98ea0475e415db2ec3300ee6084eaa050fc76f76c717b948df87b9
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T104518-2819215 ]; then cp -a /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T104518-2819215 /usr/lib/nuxel/nuxel-preload-cinema; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-preload-cinema ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-preload-cinema | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-preload-cinema)"
if [ -e /usr/lib/nuxel/nuxel-preload-cinema ] && [ ! -e /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-preload-cinema /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-preload-cinema ] && [ ! -e /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T104518-2819215 ]; then cp -a /usr/lib/nuxel/nuxel-preload-cinema /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T104518-2819215; fi
test -f /usr/lib/nuxel/nuxel-preload-cinema.nuxel-staged
printf '%s  %s\n' f4c74d3d3d98ea0475e415db2ec3300ee6084eaa050fc76f76c717b948df87b9 /usr/lib/nuxel/nuxel-preload-cinema.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-preload-cinema.nuxel-staged /usr/lib/nuxel/nuxel-preload-cinema
sha256sum /usr/lib/nuxel/nuxel-preload-cinema | grep -q f4c74d3d3d98ea0475e415db2ec3300ee6084eaa050fc76f76c717b948df87b9
echo INSTALL-OK
