#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-service-graph.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-service-graph.py
# previous-hash: 8114851de65a9bbb383da3410285eecc01c1452c64c099503ae319bf9df0ee7a
set -eu
mkdir -p "$(dirname /usr/local/bin/verify-service-graph.py)"
if [ -e /usr/local/bin/verify-service-graph.py ]; then cp -a /usr/local/bin/verify-service-graph.py /usr/local/bin/verify-service-graph.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-service-graph.py.nuxel-staged
printf '%s  %s\n' 8114851de65a9bbb383da3410285eecc01c1452c64c099503ae319bf9df0ee7a /usr/local/bin/verify-service-graph.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-service-graph.py.nuxel-staged /usr/local/bin/verify-service-graph.py
sha256sum /usr/local/bin/verify-service-graph.py | grep -q 8114851de65a9bbb383da3410285eecc01c1452c64c099503ae319bf9df0ee7a
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/verify-service-graph.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-service-graph.py.nuxel-rollback /usr/local/bin/verify-service-graph.py; true; fi
