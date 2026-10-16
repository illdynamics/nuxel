#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/build-a33-buttons.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/build-a33-buttons.sh
# previous-hash: 412e7e1857366d87fa2a2c15c65392c2e9084acf4a76dec3868e500b5a398d48
set -eu
mkdir -p "$(dirname /usr/local/bin/build-a33-buttons.sh)"
if [ -e /usr/local/bin/build-a33-buttons.sh ]; then cp -a /usr/local/bin/build-a33-buttons.sh /usr/local/bin/build-a33-buttons.sh.nuxel-rollback; fi
test -f /usr/local/bin/build-a33-buttons.sh.nuxel-staged
printf '%s  %s\n' 412e7e1857366d87fa2a2c15c65392c2e9084acf4a76dec3868e500b5a398d48 /usr/local/bin/build-a33-buttons.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/build-a33-buttons.sh.nuxel-staged /usr/local/bin/build-a33-buttons.sh
sha256sum /usr/local/bin/build-a33-buttons.sh | grep -q 412e7e1857366d87fa2a2c15c65392c2e9084acf4a76dec3868e500b5a398d48
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/build-a33-buttons.sh.nuxel-rollback ]; then cp -a /usr/local/bin/build-a33-buttons.sh.nuxel-rollback /usr/local/bin/build-a33-buttons.sh; true; fi
