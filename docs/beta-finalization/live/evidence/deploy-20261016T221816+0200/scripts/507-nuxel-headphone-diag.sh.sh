#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-headphone-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-headphone-diag.sh
# previous-hash: 4fc2f6d993c1df631f8a19a8503d93572ea831ec2eb4298aad8d7c003229ff8f
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-headphone-diag.sh)"
if [ -e /usr/local/bin/nuxel-headphone-diag.sh ]; then cp -a /usr/local/bin/nuxel-headphone-diag.sh /usr/local/bin/nuxel-headphone-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-headphone-diag.sh.nuxel-staged
printf '%s  %s\n' 4fc2f6d993c1df631f8a19a8503d93572ea831ec2eb4298aad8d7c003229ff8f /usr/local/bin/nuxel-headphone-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-headphone-diag.sh.nuxel-staged /usr/local/bin/nuxel-headphone-diag.sh
sha256sum /usr/local/bin/nuxel-headphone-diag.sh | grep -q 4fc2f6d993c1df631f8a19a8503d93572ea831ec2eb4298aad8d7c003229ff8f
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-headphone-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-headphone-diag.sh.nuxel-rollback /usr/local/bin/nuxel-headphone-diag.sh; true; fi
