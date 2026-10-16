#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-gnss-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-gnss-diag.sh
# previous-hash: 76baf8fa9493bee5578be670068895b9b686be08bedf5a4c0f07c48f6860dbb6
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-gnss-diag.sh)"
if [ -e /usr/local/bin/nuxel-gnss-diag.sh ]; then cp -a /usr/local/bin/nuxel-gnss-diag.sh /usr/local/bin/nuxel-gnss-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-gnss-diag.sh.nuxel-staged
printf '%s  %s\n' 76baf8fa9493bee5578be670068895b9b686be08bedf5a4c0f07c48f6860dbb6 /usr/local/bin/nuxel-gnss-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-gnss-diag.sh.nuxel-staged /usr/local/bin/nuxel-gnss-diag.sh
sha256sum /usr/local/bin/nuxel-gnss-diag.sh | grep -q 76baf8fa9493bee5578be670068895b9b686be08bedf5a4c0f07c48f6860dbb6
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-gnss-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-gnss-diag.sh.nuxel-rollback /usr/local/bin/nuxel-gnss-diag.sh; true; fi
