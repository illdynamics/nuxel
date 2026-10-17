#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/verify-permissions.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/verify-permissions.py
# previous-hash: cbc93c3245f3728227de0fa608b5e8629921428a9db85d27565596e821699a86
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/verify-permissions.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-permissions.py.nuxel-rollback /usr/local/bin/verify-permissions.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/verify-permissions.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/verify-permissions.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/verify-permissions.py)"
if [ -e /usr/local/bin/verify-permissions.py ] && [ ! -e /usr/local/bin/verify-permissions.py.nuxel-rollback ]; then cp -a /usr/local/bin/verify-permissions.py /usr/local/bin/verify-permissions.py.nuxel-rollback; fi
test -f /usr/local/bin/verify-permissions.py.nuxel-staged
printf '%s  %s\n' cbc93c3245f3728227de0fa608b5e8629921428a9db85d27565596e821699a86 /usr/local/bin/verify-permissions.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/verify-permissions.py.nuxel-staged /usr/local/bin/verify-permissions.py
sha256sum /usr/local/bin/verify-permissions.py | grep -q cbc93c3245f3728227de0fa608b5e8629921428a9db85d27565596e821699a86
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
