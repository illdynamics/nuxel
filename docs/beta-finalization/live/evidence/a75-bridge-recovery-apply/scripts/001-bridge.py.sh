#!/bin/sh
# A75 shared system-bus bridge startup recovery -> /usr/lib/nuxel/nuxel-bridge/bridge.py (service: nuxel-bridge.service, risk: medium)
# staged source: services/nuxel-bridge/src/bridge.py
# previous-hash: 082349d170bdb8f46fef905ca92c63e604237f415650da66a6d2ae765a2354f5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback /usr/lib/nuxel/nuxel-bridge/bridge.py; systemctl restart nuxel-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/bridge.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged
printf '%s  %s\n' 082349d170bdb8f46fef905ca92c63e604237f415650da66a6d2ae765a2354f5 /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/bridge.py
sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | grep -q 082349d170bdb8f46fef905ca92c63e604237f415650da66a6d2ae765a2354f5
systemctl restart nuxel-bridge.service
systemctl is-active nuxel-bridge.service
echo INSTALL-OK
