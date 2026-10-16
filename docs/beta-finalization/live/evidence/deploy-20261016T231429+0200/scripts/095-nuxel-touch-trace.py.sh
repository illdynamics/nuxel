#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/libexec/nuxel/nuxel-touch-trace.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-touch-trace.py
# previous-hash: dc3a0d61ec4396b0bf55b58297f0801a4d773a120b945aee6bbac06e24709484
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-rollback /usr/libexec/nuxel/nuxel-touch-trace.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/libexec/nuxel/nuxel-touch-trace.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/libexec/nuxel/nuxel-touch-trace.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-touch-trace.py)"
if [ -e /usr/libexec/nuxel/nuxel-touch-trace.py ] && [ ! -e /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-touch-trace.py /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-staged
printf '%s  %s\n' dc3a0d61ec4396b0bf55b58297f0801a4d773a120b945aee6bbac06e24709484 /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-staged /usr/libexec/nuxel/nuxel-touch-trace.py
sha256sum /usr/libexec/nuxel/nuxel-touch-trace.py | grep -q dc3a0d61ec4396b0bf55b58297f0801a4d773a120b945aee6bbac06e24709484
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
