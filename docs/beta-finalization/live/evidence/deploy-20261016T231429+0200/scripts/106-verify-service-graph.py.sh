#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-service-graph.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-service-graph.py
# previous-hash: 8114851de65a9bbb383da3410285eecc01c1452c64c099503ae319bf9df0ee7a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/verify-service-graph.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-service-graph.py.nuxel-rollback /usr/local/bin/verify-service-graph.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/verify-service-graph.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/verify-service-graph.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/verify-service-graph.py)"
if [ -e /usr/local/bin/verify-service-graph.py ] && [ ! -e /usr/local/bin/verify-service-graph.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-service-graph.py /usr/local/bin/verify-service-graph.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-service-graph.py.nuxel-staged
printf '%s  %s\n' 8114851de65a9bbb383da3410285eecc01c1452c64c099503ae319bf9df0ee7a /usr/local/bin/verify-service-graph.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-service-graph.py.nuxel-staged /usr/local/bin/verify-service-graph.py
sha256sum /usr/local/bin/verify-service-graph.py | grep -q 8114851de65a9bbb383da3410285eecc01c1452c64c099503ae319bf9df0ee7a
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
