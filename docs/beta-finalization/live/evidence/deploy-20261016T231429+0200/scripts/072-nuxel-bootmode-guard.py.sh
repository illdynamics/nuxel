#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/libexec/nuxel/nuxel-bootmode-guard.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-bootmode-guard.py
# previous-hash: 0019ce964d7499f25df13fbbb2a6c07371139c661780223cae7e17f83ec6fce0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-rollback /usr/libexec/nuxel/nuxel-bootmode-guard.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/libexec/nuxel/nuxel-bootmode-guard.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/libexec/nuxel/nuxel-bootmode-guard.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-bootmode-guard.py)"
if [ -e /usr/libexec/nuxel/nuxel-bootmode-guard.py ] && [ ! -e /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-bootmode-guard.py /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-staged
printf '%s  %s\n' 0019ce964d7499f25df13fbbb2a6c07371139c661780223cae7e17f83ec6fce0 /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-bootmode-guard.py.nuxel-staged /usr/libexec/nuxel/nuxel-bootmode-guard.py
sha256sum /usr/libexec/nuxel/nuxel-bootmode-guard.py | grep -q 0019ce964d7499f25df13fbbb2a6c07371139c661780223cae7e17f83ec6fce0
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
