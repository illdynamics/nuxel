#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-mt.h (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-mt.h
# previous-hash: 18db81abdc4f3ec68485d764a402194b936717f6a68ab2032b1032671b3edf82
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-mt.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-mt.h.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-mt.h; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-mt.h ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-mt.h | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-mt.h)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-mt.h ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-mt.h.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-mt.h /usr/lib/nuxel/src/a33/nuxel-mt.h.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-mt.h.nuxel-staged
printf '%s  %s\n' 18db81abdc4f3ec68485d764a402194b936717f6a68ab2032b1032671b3edf82 /usr/lib/nuxel/src/a33/nuxel-mt.h.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-mt.h.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-mt.h
sha256sum /usr/lib/nuxel/src/a33/nuxel-mt.h | grep -q 18db81abdc4f3ec68485d764a402194b936717f6a68ab2032b1032671b3edf82
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
