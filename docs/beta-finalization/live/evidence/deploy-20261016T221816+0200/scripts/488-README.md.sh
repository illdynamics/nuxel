#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/README.md (service: None, risk: medium)
# staged source: tools/s10plus/a33/README.md
# previous-hash: 2160719a9f26aebace6135056b028d1c873eac0044d6977db368c35bbd09678a
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/README.md)"
if [ -e /usr/lib/nuxel/src/a33/README.md ]; then cp -a /usr/lib/nuxel/src/a33/README.md /usr/lib/nuxel/src/a33/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/README.md.nuxel-staged
printf '%s  %s\n' 2160719a9f26aebace6135056b028d1c873eac0044d6977db368c35bbd09678a /usr/lib/nuxel/src/a33/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/README.md.nuxel-staged /usr/lib/nuxel/src/a33/README.md
sha256sum /usr/lib/nuxel/src/a33/README.md | grep -q 2160719a9f26aebace6135056b028d1c873eac0044d6977db368c35bbd09678a
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/a33/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/README.md.nuxel-rollback /usr/lib/nuxel/src/a33/README.md; true; fi
