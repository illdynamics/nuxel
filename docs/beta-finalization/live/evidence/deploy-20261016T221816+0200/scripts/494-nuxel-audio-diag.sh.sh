#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-audio-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-audio-diag.sh
# previous-hash: 0d5475367c8b5d9030176d3756f01ffecfddb56417fb8dbcc7a482bca298e21f
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-audio-diag.sh)"
if [ -e /usr/local/bin/nuxel-audio-diag.sh ]; then cp -a /usr/local/bin/nuxel-audio-diag.sh /usr/local/bin/nuxel-audio-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-audio-diag.sh.nuxel-staged
printf '%s  %s\n' 0d5475367c8b5d9030176d3756f01ffecfddb56417fb8dbcc7a482bca298e21f /usr/local/bin/nuxel-audio-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-audio-diag.sh.nuxel-staged /usr/local/bin/nuxel-audio-diag.sh
sha256sum /usr/local/bin/nuxel-audio-diag.sh | grep -q 0d5475367c8b5d9030176d3756f01ffecfddb56417fb8dbcc7a482bca298e21f
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-audio-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-audio-diag.sh.nuxel-rollback /usr/local/bin/nuxel-audio-diag.sh; true; fi
