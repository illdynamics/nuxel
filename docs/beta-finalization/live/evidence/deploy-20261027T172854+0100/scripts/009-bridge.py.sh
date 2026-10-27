#!/bin/sh
# nuxel-bridge D-Bus provider (firmware-aware Bluetooth status) -> /usr/lib/nuxel/nuxel-bridge/bridge.py (service: nuxel-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/bridge.py
# previous-hash: 7b5277dbb257c034e37e577be785425ae2007a5999e53e20bfa86b61ab9bf068
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T172854-2155739 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T172854-2155739 /usr/lib/nuxel/nuxel-bridge/bridge.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
test -d /usr/lib/nuxel/nuxel-bridge
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/bridge.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T172854-2155739 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T172854-2155739; fi
test -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged
printf '%s  %s\n' 7b5277dbb257c034e37e577be785425ae2007a5999e53e20bfa86b61ab9bf068 /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/bridge.py
sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | grep -q 7b5277dbb257c034e37e577be785425ae2007a5999e53e20bfa86b61ab9bf068
echo INSTALL-OK
