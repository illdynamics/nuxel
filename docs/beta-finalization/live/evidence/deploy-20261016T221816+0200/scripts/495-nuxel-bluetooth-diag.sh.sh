#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-bluetooth-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-bluetooth-diag.sh
# previous-hash: 21c78ca70d6a08eebd25454e02042a4cc29fb2cbb8ee35aa10feaba6cbc80c59
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-bluetooth-diag.sh)"
if [ -e /usr/local/bin/nuxel-bluetooth-diag.sh ]; then cp -a /usr/local/bin/nuxel-bluetooth-diag.sh /usr/local/bin/nuxel-bluetooth-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-bluetooth-diag.sh.nuxel-staged
printf '%s  %s\n' 21c78ca70d6a08eebd25454e02042a4cc29fb2cbb8ee35aa10feaba6cbc80c59 /usr/local/bin/nuxel-bluetooth-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-bluetooth-diag.sh.nuxel-staged /usr/local/bin/nuxel-bluetooth-diag.sh
sha256sum /usr/local/bin/nuxel-bluetooth-diag.sh | grep -q 21c78ca70d6a08eebd25454e02042a4cc29fb2cbb8ee35aa10feaba6cbc80c59
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-bluetooth-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-bluetooth-diag.sh.nuxel-rollback /usr/local/bin/nuxel-bluetooth-diag.sh; true; fi
