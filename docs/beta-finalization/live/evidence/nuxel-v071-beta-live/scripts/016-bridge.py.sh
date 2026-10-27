#!/bin/sh
# v0.7.1-beta bridge, notification and portal version pins -> /usr/lib/nuxel/nuxel-bridge/bridge.py (service: None, risk: medium)
# staged source: services/nuxel-bridge/src/bridge.py
# previous-hash: 4d296f54bced4ed823a9b7acb7793558f62c86979fc9dd8d9070a19356481abb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T214530-2399261 /usr/lib/nuxel/nuxel-bridge/bridge.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/bridge.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged
printf '%s  %s\n' 4d296f54bced4ed823a9b7acb7793558f62c86979fc9dd8d9070a19356481abb /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/bridge.py
sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | grep -q 4d296f54bced4ed823a9b7acb7793558f62c86979fc9dd8d9070a19356481abb
echo INSTALL-OK
