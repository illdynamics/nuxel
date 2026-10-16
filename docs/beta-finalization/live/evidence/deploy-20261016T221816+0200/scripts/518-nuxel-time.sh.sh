#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-time.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-time.sh
# previous-hash: 15acea3964bbef454c3c07604645a6dba453fb0d683626ace42b0ac488aa3175
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-time.sh)"
if [ -e /usr/local/bin/nuxel-time.sh ]; then cp -a /usr/local/bin/nuxel-time.sh /usr/local/bin/nuxel-time.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-time.sh.nuxel-staged
printf '%s  %s\n' 15acea3964bbef454c3c07604645a6dba453fb0d683626ace42b0ac488aa3175 /usr/local/bin/nuxel-time.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-time.sh.nuxel-staged /usr/local/bin/nuxel-time.sh
sha256sum /usr/local/bin/nuxel-time.sh | grep -q 15acea3964bbef454c3c07604645a6dba453fb0d683626ace42b0ac488aa3175
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-time.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-time.sh.nuxel-rollback /usr/local/bin/nuxel-time.sh; true; fi
