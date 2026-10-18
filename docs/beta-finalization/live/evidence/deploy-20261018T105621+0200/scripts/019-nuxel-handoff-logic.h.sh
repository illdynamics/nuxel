#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-handoff-logic.h
# previous-hash: 56f42be479b345be69ffefd8dd0e02d16b7a720bff1d2cfb34158f1a39471aaf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-staged
printf '%s  %s\n' 56f42be479b345be69ffefd8dd0e02d16b7a720bff1d2cfb34158f1a39471aaf /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h
sha256sum /usr/lib/nuxel/src/a33/nuxel-handoff-logic.h | grep -q 56f42be479b345be69ffefd8dd0e02d16b7a720bff1d2cfb34158f1a39471aaf
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
