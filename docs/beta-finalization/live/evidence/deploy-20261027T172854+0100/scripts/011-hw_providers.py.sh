#!/bin/sh
# nuxel-http-bridge root hardware providers (audio/display/bluetooth-power) -> /usr/lib/nuxel/nuxel-bridge/hw_providers.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/hw_providers.py
# previous-hash: 5402963986654f74282d728b870bbaf7b685c2afcafd2a681faf70ae5d1d77e7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T172854-2155739 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T172854-2155739 /usr/lib/nuxel/nuxel-bridge/hw_providers.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /usr/lib/nuxel/nuxel-bridge
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/hw_providers.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/hw_providers.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T172854-2155739 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T172854-2155739; fi
test -f /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged
printf '%s  %s\n' 5402963986654f74282d728b870bbaf7b685c2afcafd2a681faf70ae5d1d77e7 /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/hw_providers.py
sha256sum /usr/lib/nuxel/nuxel-bridge/hw_providers.py | grep -q 5402963986654f74282d728b870bbaf7b685c2afcafd2a681faf70ae5d1d77e7
echo INSTALL-OK
