#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-wl-fb.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-wl-fb.c
# previous-hash: 052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-wl-fb.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-wl-fb.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-wl-fb.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-wl-fb.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-wl-fb.c ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-wl-fb.c /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-staged
printf '%s  %s\n' 052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768 /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-wl-fb.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-wl-fb.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-wl-fb.c | grep -q 052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
