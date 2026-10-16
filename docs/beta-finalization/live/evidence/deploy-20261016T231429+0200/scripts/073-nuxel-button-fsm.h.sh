#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-button-fsm.h (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-button-fsm.h
# previous-hash: 63022c354c6557432091dadc27c14898a99bb2ac55f8df5a121048e2a4eb597a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-button-fsm.h; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-button-fsm.h | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-button-fsm.h)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged
printf '%s  %s\n' 63022c354c6557432091dadc27c14898a99bb2ac55f8df5a121048e2a4eb597a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-button-fsm.h
sha256sum /usr/lib/nuxel/src/a33/nuxel-button-fsm.h | grep -q 63022c354c6557432091dadc27c14898a99bb2ac55f8df5a121048e2a4eb597a
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
