#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-led-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-led-diag.sh
# previous-hash: d24124105fdcedb056dcec0c3aee9b010d26b42ae01397bfe733393670532b83
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-led-diag.sh)"
if [ -e /usr/local/bin/nuxel-led-diag.sh ]; then cp -a /usr/local/bin/nuxel-led-diag.sh /usr/local/bin/nuxel-led-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-led-diag.sh.nuxel-staged
printf '%s  %s\n' d24124105fdcedb056dcec0c3aee9b010d26b42ae01397bfe733393670532b83 /usr/local/bin/nuxel-led-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-led-diag.sh.nuxel-staged /usr/local/bin/nuxel-led-diag.sh
sha256sum /usr/local/bin/nuxel-led-diag.sh | grep -q d24124105fdcedb056dcec0c3aee9b010d26b42ae01397bfe733393670532b83
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-led-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-led-diag.sh.nuxel-rollback /usr/local/bin/nuxel-led-diag.sh; true; fi
