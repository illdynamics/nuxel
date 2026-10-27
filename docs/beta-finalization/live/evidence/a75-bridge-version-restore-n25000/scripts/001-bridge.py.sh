#!/bin/sh
# nuxel-bridge D-Bus service code (Wi-Fi scan timeout bound + version pin) -> /usr/lib/nuxel/nuxel-bridge/bridge.py (service: nuxel-bridge.service, risk: medium)
# staged source: services/nuxel-bridge/src/bridge.py
# previous-hash: 03d1349444cbba752a9e9b0690a40756b177c25b1c9d235276fda1a2e29fafca
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback /usr/lib/nuxel/nuxel-bridge/bridge.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/bridge.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged
printf '%s  %s\n' 03d1349444cbba752a9e9b0690a40756b177c25b1c9d235276fda1a2e29fafca /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/bridge.py
sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | grep -q 03d1349444cbba752a9e9b0690a40756b177c25b1c9d235276fda1a2e29fafca
echo INSTALL-OK
