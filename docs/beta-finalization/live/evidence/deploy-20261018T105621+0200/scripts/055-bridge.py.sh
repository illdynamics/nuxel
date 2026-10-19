#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-bridge/bridge.py (service: None, risk: medium)
# staged source: services/nuxel-bridge/src/bridge.py
# previous-hash: fcc4c29d880c7d72fa951c0038bc331e0ea8872c1da3e6eea1b1c7a5ad214637
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback /usr/lib/nuxel/nuxel-bridge/bridge.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/bridge.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/bridge.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/bridge.py /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged
printf '%s  %s\n' fcc4c29d880c7d72fa951c0038bc331e0ea8872c1da3e6eea1b1c7a5ad214637 /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/bridge.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/bridge.py
sha256sum /usr/lib/nuxel/nuxel-bridge/bridge.py | grep -q fcc4c29d880c7d72fa951c0038bc331e0ea8872c1da3e6eea1b1c7a5ad214637
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
