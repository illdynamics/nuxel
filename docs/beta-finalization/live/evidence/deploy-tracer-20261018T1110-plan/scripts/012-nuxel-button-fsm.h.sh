#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-button-fsm.h (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-button-fsm.h
# previous-hash: ff06992306370923ebd8c613c7ad0f8a950fb69c59687de4130b7242642795bf
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-button-fsm.h; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-button-fsm.h | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-button-fsm.h)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-button-fsm.h /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged
printf '%s  %s\n' ff06992306370923ebd8c613c7ad0f8a950fb69c59687de4130b7242642795bf /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-button-fsm.h.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-button-fsm.h
sha256sum /usr/lib/nuxel/src/a33/nuxel-button-fsm.h | grep -q ff06992306370923ebd8c613c7ad0f8a950fb69c59687de4130b7242642795bf
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
