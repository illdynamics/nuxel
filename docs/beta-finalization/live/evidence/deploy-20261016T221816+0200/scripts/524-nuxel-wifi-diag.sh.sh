#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-wifi-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-wifi-diag.sh
# previous-hash: 7120edb3373071cddb11d251a24473951efbdce613d383f697bfcc1ece247076
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-wifi-diag.sh)"
if [ -e /usr/local/bin/nuxel-wifi-diag.sh ]; then cp -a /usr/local/bin/nuxel-wifi-diag.sh /usr/local/bin/nuxel-wifi-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-wifi-diag.sh.nuxel-staged
printf '%s  %s\n' 7120edb3373071cddb11d251a24473951efbdce613d383f697bfcc1ece247076 /usr/local/bin/nuxel-wifi-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-wifi-diag.sh.nuxel-staged /usr/local/bin/nuxel-wifi-diag.sh
sha256sum /usr/local/bin/nuxel-wifi-diag.sh | grep -q 7120edb3373071cddb11d251a24473951efbdce613d383f697bfcc1ece247076
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-wifi-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-wifi-diag.sh.nuxel-rollback /usr/local/bin/nuxel-wifi-diag.sh; true; fi
