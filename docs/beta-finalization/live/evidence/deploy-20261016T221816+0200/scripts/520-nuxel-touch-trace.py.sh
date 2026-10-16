#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/libexec/nuxel/nuxel-touch-trace.py (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-touch-trace.py
# previous-hash: dc3a0d61ec4396b0bf55b58297f0801a4d773a120b945aee6bbac06e24709484
set -eu
mkdir -p "$(dirname /usr/libexec/nuxel/nuxel-touch-trace.py)"
if [ -e /usr/libexec/nuxel/nuxel-touch-trace.py ]; then cp -a /usr/libexec/nuxel/nuxel-touch-trace.py /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-rollback; fi
test -f /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-staged
printf '%s  %s\n' dc3a0d61ec4396b0bf55b58297f0801a4d773a120b945aee6bbac06e24709484 /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-staged /usr/libexec/nuxel/nuxel-touch-trace.py
sha256sum /usr/libexec/nuxel/nuxel-touch-trace.py | grep -q dc3a0d61ec4396b0bf55b58297f0801a4d773a120b945aee6bbac06e24709484
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-rollback ]; then cp -a /usr/libexec/nuxel/nuxel-touch-trace.py.nuxel-rollback /usr/libexec/nuxel/nuxel-touch-trace.py; true; fi
