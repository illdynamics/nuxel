#!/bin/sh
# AudioProvider bounded scontrols discovery -> /usr/lib/nuxel/nuxel-bridge/hw_providers.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/hw_providers.py
# previous-hash: d67df7a05bc55837e2f26b12297537352290ae3249f8244e57b7fa12d953d62b
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-v070-hotfix ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-v070-hotfix /usr/lib/nuxel/nuxel-bridge/hw_providers.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/hw_providers.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/hw_providers.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-v070-hotfix ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-v070-hotfix; fi
test -f /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged
printf '%s  %s\n' d67df7a05bc55837e2f26b12297537352290ae3249f8244e57b7fa12d953d62b /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/hw_providers.py
sha256sum /usr/lib/nuxel/nuxel-bridge/hw_providers.py | grep -q d67df7a05bc55837e2f26b12297537352290ae3249f8244e57b7fa12d953d62b
echo INSTALL-OK
