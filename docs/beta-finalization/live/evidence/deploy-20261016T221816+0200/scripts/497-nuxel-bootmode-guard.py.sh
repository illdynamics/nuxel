#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/libexec/nuxel/nuxel-bootmode-guard.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-bootmode-guard.py
# previous-hash: 0019ce964d7499f25df13fbbb2a6c07371139c661780223cae7e17f83ec6fce0
set -eu
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-bootmode-guard.py)"
if [ -e /usr/libexec/nuxel/nuxel-bootmode-guard.py ]; then cp -a /usr/libexec/nuxel/nuxel-bootmode-guard.py /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-staged
printf '%s  %s\n' 0019ce964d7499f25df13fbbb2a6c07371139c661780223cae7e17f83ec6fce0 /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-staged /usr/libexec/nuxel/nuxel-bootmode-guard.py
sha256sum /usr/libexec/nuxel/nuxel-bootmode-guard.py | grep -q 0019ce964d7499f25df13fbbb2a6c07371139c661780223cae7e17f83ec6fce0
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-rollback /usr/libexec/nuxel/nuxel-bootmode-guard.py; true; fi
