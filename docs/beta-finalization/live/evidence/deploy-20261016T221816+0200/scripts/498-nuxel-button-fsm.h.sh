#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-button-fsm.h (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-button-fsm.h
# previous-hash: 63022c354c6557432091dadc27c14898a99bb2ac55f8df5a121048e2a4eb597a
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-button-fsm.h)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged
printf '%s  %s\n' 63022c354c6557432091dadc27c14898a99bb2ac55f8df5a121048e2a4eb597a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-button-fsm.h
sha256sum /usr/lib/nuxel/src/a33/nuxel-button-fsm.h | grep -q 63022c354c6557432091dadc27c14898a99bb2ac55f8df5a121048e2a4eb597a
systemctl daemon-reload
systemctl daemon-reload
test -x /usr/local/bin/nuxelctl && test -x /usr/libexec/nuxel/nuxel-verbose-boot && test -s /usr/share/nuxel/probes/touch-probe.html && test -x /usr/local/bin/nuxel-fb-owner-assert.sh
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-button-fsm.h; true; fi
