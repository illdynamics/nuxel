#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/share/nuxel/probes/touch-probe.html (service: None, risk: medium)
# staged source: tools/s10plus/a33/touch-probe.html
# previous-hash: aea597a1b6cb77a5e7af497a63a4900b59000498a8ccedf6d5998ae8371aad21
set -eu
mkdir -p "$(dirname /usr/share/nuxel/probes/touch-probe.html)"
if [ -e /usr/share/nuxel/probes/touch-probe.html ]; then cp -a /usr/share/nuxel/probes/touch-probe.html /usr/share/nuxel/probes/touch-probe.html.nuxel-rollback; fi
test -f /usr/share/nuxel/probes/touch-probe.html.nuxel-staged
printf '%s  %s\n' aea597a1b6cb77a5e7af497a63a4900b59000498a8ccedf6d5998ae8371aad21 /usr/share/nuxel/probes/touch-probe.html.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/probes/touch-probe.html.nuxel-staged /usr/share/nuxel/probes/touch-probe.html
sha256sum /usr/share/nuxel/probes/touch-probe.html | grep -q aea597a1b6cb77a5e7af497a63a4900b59000498a8ccedf6d5998ae8371aad21
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/share/nuxel/probes/touch-probe.html.nuxel-rollback ]; then cp -a /usr/share/nuxel/probes/touch-probe.html.nuxel-rollback /usr/share/nuxel/probes/touch-probe.html; true; fi
