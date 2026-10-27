#!/bin/sh
# nuxel-http-bridge audio/display/Bluetooth power providers -> /usr/lib/nuxel/nuxel-bridge/hw_providers.py (service: nuxel-http-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/hw_providers.py
# previous-hash: 94978a2589c369b0536222152af574d5d79f8a4f0b2ae8f5a35cca5ca78496ed
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T182142-2202036 /usr/lib/nuxel/nuxel-bridge/hw_providers.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/hw_providers.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/hw_providers.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/hw_providers.py /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-rollback.pre-deploy-20261027T182142-2202036; fi
test -f /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged
printf '%s  %s\n' 94978a2589c369b0536222152af574d5d79f8a4f0b2ae8f5a35cca5ca78496ed /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/hw_providers.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/hw_providers.py
sha256sum /usr/lib/nuxel/nuxel-bridge/hw_providers.py | grep -q 94978a2589c369b0536222152af574d5d79f8a4f0b2ae8f5a35cca5ca78496ed
echo INSTALL-OK
