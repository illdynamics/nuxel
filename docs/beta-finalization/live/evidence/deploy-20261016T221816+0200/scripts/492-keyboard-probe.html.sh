#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/share/nuxel/probes/keyboard-probe.html (service: None, risk: medium)
# staged source: tools/s10plus/a33/keyboard-probe.html
# previous-hash: 23fed0b72e8e9f3832de7f1674edf727004e06eb317dc1e2464e4d005268ec09
set -eu
mkdir -p "$(dirname /usr/share/nuxel/probes/keyboard-probe.html)"
if [ -e /usr/share/nuxel/probes/keyboard-probe.html ]; then cp -a /usr/share/nuxel/probes/keyboard-probe.html /usr/share/nuxel/probes/keyboard-probe.html.nuxel-rollback; fi
test -f /usr/share/nuxel/probes/keyboard-probe.html.nuxel-staged
printf '%s  %s\n' 23fed0b72e8e9f3832de7f1674edf727004e06eb317dc1e2464e4d005268ec09 /usr/share/nuxel/probes/keyboard-probe.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/probes/keyboard-probe.html.nuxel-staged /usr/share/nuxel/probes/keyboard-probe.html
sha256sum /usr/share/nuxel/probes/keyboard-probe.html | grep -q 23fed0b72e8e9f3832de7f1674edf727004e06eb317dc1e2464e4d005268ec09
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/probes/keyboard-probe.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/probes/keyboard-probe.html.nuxel-rollback /usr/share/nuxel/probes/keyboard-probe.html; true; fi
