#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-haptics-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-haptics-diag.sh
# previous-hash: b48458ebcdcc06705b8bd11253fa2ef7e2ad2da4b1a53f8c1ea7a97e7615460b
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-haptics-diag.sh)"
if [ -e /usr/local/bin/nuxel-haptics-diag.sh ]; then cp -a /usr/local/bin/nuxel-haptics-diag.sh /usr/local/bin/nuxel-haptics-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-haptics-diag.sh.nuxel-staged
printf '%s  %s\n' b48458ebcdcc06705b8bd11253fa2ef7e2ad2da4b1a53f8c1ea7a97e7615460b /usr/local/bin/nuxel-haptics-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-haptics-diag.sh.nuxel-staged /usr/local/bin/nuxel-haptics-diag.sh
sha256sum /usr/local/bin/nuxel-haptics-diag.sh | grep -q b48458ebcdcc06705b8bd11253fa2ef7e2ad2da4b1a53f8c1ea7a97e7615460b
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-haptics-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-haptics-diag.sh.nuxel-rollback /usr/local/bin/nuxel-haptics-diag.sh; true; fi
