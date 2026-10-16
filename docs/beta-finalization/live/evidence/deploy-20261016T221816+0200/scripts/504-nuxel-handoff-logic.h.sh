#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-handoff-logic.h
# previous-hash: 56f42be479b345be69ffefd8dd0e02d16b7a720bff1d2cfb34158f1a39471aaf
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-staged
printf '%s  %s\n' 56f42be479b345be69ffefd8dd0e02d16b7a720bff1d2cfb34158f1a39471aaf /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h
sha256sum /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h | grep -q 56f42be479b345be69ffefd8dd0e02d16b7a720bff1d2cfb34158f1a39471aaf
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h; true; fi
