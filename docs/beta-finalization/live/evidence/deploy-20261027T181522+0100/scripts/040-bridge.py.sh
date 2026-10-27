#!/bin/sh
# nuxel-bridge Bluetooth/location providers and media store -> /usr/lib/nuxel/nuxel-bridge/bridge.py (service: nuxel-bridge, risk: medium)
# staged source: services/nuxel-bridge/src/bridge.py
# previous-hash: 7b3b627da22b37889372472e1eb9c665d26ccd7afa6835063571ceb6e3d06623
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T181522-2198480 /usr/lib/nuxel/nuxel-bridge/bridge.py; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/bridge.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback; fi
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T181522-2198480 ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback.pre-deploy-20261027T181522-2198480; fi
test -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged
printf '%s  %s\n' 7b3b627da22b37889372472e1eb9c665d26ccd7afa6835063571ceb6e3d06623 /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/bridge.py
sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | grep -q 7b3b627da22b37889372472e1eb9c665d26ccd7afa6835063571ceb6e3d06623
echo INSTALL-OK
