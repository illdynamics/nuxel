#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-button-manager.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-button-manager.c
# previous-hash: d1a83d74222734053d4cd1b66fbf6563ec13d25e40364a3bcdd7d2d67f22032b
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-button-manager.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-manager.c ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-manager.c /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-staged
printf '%s  %s\n' d1a83d74222734053d4cd1b66fbf6563ec13d25e40364a3bcdd7d2d67f22032b /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-button-manager.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-button-manager.c | grep -q d1a83d74222734053d4cd1b66fbf6563ec13d25e40364a3bcdd7d2d67f22032b
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-manager.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-button-manager.c; true; fi
