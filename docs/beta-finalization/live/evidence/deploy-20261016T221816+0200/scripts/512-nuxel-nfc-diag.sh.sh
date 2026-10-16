#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-nfc-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-nfc-diag.sh
# previous-hash: 93546a357e4fa6e564b9739e99976f9d1e913bdd270b339ee964a46a5fceb9f8
set -eu
mkdir -p "$(dirname /usr/local/bin/nuxel-nfc-diag.sh)"
if [ -e /usr/local/bin/nuxel-nfc-diag.sh ]; then cp -a /usr/local/bin/nuxel-nfc-diag.sh /usr/local/bin/nuxel-nfc-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-nfc-diag.sh.nuxel-staged
printf '%s  %s\n' 93546a357e4fa6e564b9739e99976f9d1e913bdd270b339ee964a46a5fceb9f8 /usr/local/bin/nuxel-nfc-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-nfc-diag.sh.nuxel-staged /usr/local/bin/nuxel-nfc-diag.sh
sha256sum /usr/local/bin/nuxel-nfc-diag.sh | grep -q 93546a357e4fa6e564b9739e99976f9d1e913bdd270b339ee964a46a5fceb9f8
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/local/bin/nuxel-nfc-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-nfc-diag.sh.nuxel-rollback /usr/local/bin/nuxel-nfc-diag.sh; true; fi
