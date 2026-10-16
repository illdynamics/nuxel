#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-keyboard-apply.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-keyboard-apply.sh
# previous-hash: 2794f65d2b9c8a6efda18b68e3b13f6f19338be0dd55c5fabde767ad87f40d50
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-keyboard-apply.sh)"
if [ -e /usr/local/bin/nuxel-keyboard-apply.sh ]; then cp -a /usr/local/bin/nuxel-keyboard-apply.sh /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-staged
printf '%s  %s\n' 2794f65d2b9c8a6efda18b68e3b13f6f19338be0dd55c5fabde767ad87f40d50 /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-staged /usr/local/bin/nuxel-keyboard-apply.sh
sha256sum /usr/local/bin/nuxel-keyboard-apply.sh | grep -q 2794f65d2b9c8a6efda18b68e3b13f6f19338be0dd55c5fabde767ad87f40d50
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-keyboard-apply.sh.nuxel-rollback /usr/local/bin/nuxel-keyboard-apply.sh; true; fi
