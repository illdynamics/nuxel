#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /usr/lib/nuxel/nuxel-bridge/capabilities.py (service: None, risk: medium)
# staged source: services/nuxel-bridge/src/capabilities.py
# previous-hash: b8efdd7d021d00a7438d71c66aee477339ec3819e21bdc84bb1637afb68bee8c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-bridge/capabilities.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/capabilities.py.nuxel-rollback /usr/lib/nuxel/nuxel-bridge/capabilities.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-bridge/capabilities.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-bridge/capabilities.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-bridge/capabilities.py)"
if [ -e /usr/lib/nuxel/nuxel-bridge/capabilities.py ] && [ ! -e /usr/lib/nuxel/nuxel-bridge/capabilities.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-bridge/capabilities.py /usr/lib/nuxel/nuxel-bridge/capabilities.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-bridge/capabilities.py.nuxel-staged
printf '%s  %s\n' b8efdd7d021d00a7438d71c66aee477339ec3819e21bdc84bb1637afb68bee8c /usr/lib/nuxel/nuxel-bridge/capabilities.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-bridge/capabilities.py.nuxel-staged /usr/lib/nuxel/nuxel-bridge/capabilities.py
sha256sum /usr/lib/nuxel/nuxel-bridge/capabilities.py | grep -q b8efdd7d021d00a7438d71c66aee477339ec3819e21bdc84bb1637afb68bee8c
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
