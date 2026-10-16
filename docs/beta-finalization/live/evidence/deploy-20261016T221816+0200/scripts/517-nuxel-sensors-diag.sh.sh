#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-sensors-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-sensors-diag.sh
# previous-hash: 3e5870abe2f4b80fa82a835e83d6a997bdd09ec3bc0b5f2d5d7819703b8f1c22
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-sensors-diag.sh)"
if [ -e /usr/local/bin/nuxel-sensors-diag.sh ]; then cp -a /usr/local/bin/nuxel-sensors-diag.sh /usr/local/bin/nuxel-sensors-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-sensors-diag.sh.nuxel-staged
printf '%s  %s\n' 3e5870abe2f4b80fa82a835e83d6a997bdd09ec3bc0b5f2d5d7819703b8f1c22 /usr/local/bin/nuxel-sensors-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-sensors-diag.sh.nuxel-staged /usr/local/bin/nuxel-sensors-diag.sh
sha256sum /usr/local/bin/nuxel-sensors-diag.sh | grep -q 3e5870abe2f4b80fa82a835e83d6a997bdd09ec3bc0b5f2d5d7819703b8f1c22
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-sensors-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-sensors-diag.sh.nuxel-rollback /usr/local/bin/nuxel-sensors-diag.sh; true; fi
