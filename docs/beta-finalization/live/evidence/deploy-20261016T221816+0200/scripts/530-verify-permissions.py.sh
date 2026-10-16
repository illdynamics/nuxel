#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-permissions.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-permissions.py
# previous-hash: cbc93c3245f3728227de0fa608b5e8629921428a9db85d27565596e821699a86
set -eu
mkdir -p "$(dirname /usr/local/bin/verify-permissions.py)"
if [ -e /usr/local/bin/verify-permissions.py ]; then cp -a /usr/local/bin/verify-permissions.py /usr/local/bin/verify-permissions.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-permissions.py.nuxel-staged
printf '%s  %s\n' cbc93c3245f3728227de0fa608b5e8629921428a9db85d27565596e821699a86 /usr/local/bin/verify-permissions.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-permissions.py.nuxel-staged /usr/local/bin/verify-permissions.py
sha256sum /usr/local/bin/verify-permissions.py | grep -q cbc93c3245f3728227de0fa608b5e8629921428a9db85d27565596e821699a86
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/verify-permissions.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-permissions.py.nuxel-rollback /usr/local/bin/verify-permissions.py; true; fi
