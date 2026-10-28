#!/bin/sh
# Bounded pre-lockscreen video controller, systemd unit, durable config and supplied clip -> /usr/lib/nuxel/nuxel-preload-cinema (service: None, risk: low)
# staged source: services/nuxel-preload-cinema/nuxel-preload-cinema
# previous-hash: 93b7acf6f3c10e10fb3cdac00b1ac453aa0c9ba8985026897c4e5732d107801e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T105005-2828527 ]; then cp -a /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T105005-2828527 /usr/lib/nuxel/nuxel-preload-cinema; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-preload-cinema ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-preload-cinema | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-preload-cinema)"
if [ -e /usr/lib/nuxel/nuxel-preload-cinema ] && [ ! -e /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-preload-cinema /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-preload-cinema ] && [ ! -e /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T105005-2828527 ]; then cp -a /usr/lib/nuxel/nuxel-preload-cinema /usr/lib/nuxel/nuxel-preload-cinema.nuxel-rollback.pre-deploy-20261028T105005-2828527; fi
test -f /usr/lib/nuxel/nuxel-preload-cinema.nuxel-staged
printf '%s  %s\n' 93b7acf6f3c10e10fb3cdac00b1ac453aa0c9ba8985026897c4e5732d107801e /usr/lib/nuxel/nuxel-preload-cinema.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-preload-cinema.nuxel-staged /usr/lib/nuxel/nuxel-preload-cinema
sha256sum /usr/lib/nuxel/nuxel-preload-cinema | grep -q 93b7acf6f3c10e10fb3cdac00b1ac453aa0c9ba8985026897c4e5732d107801e
echo INSTALL-OK
