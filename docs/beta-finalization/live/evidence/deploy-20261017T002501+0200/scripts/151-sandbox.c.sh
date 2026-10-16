#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/sandbox.c
# previous-hash: e147591ca5853d57b25e28c6bc005a89c09f38272cfafbc35423e1678a7f8d85
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c.nuxel-staged
printf '%s  %s\n' e147591ca5853d57b25e28c6bc005a89c09f38272cfafbc35423e1678a7f8d85 /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-sandbox/sandbox.c | grep -q e147591ca5853d57b25e28c6bc005a89c09f38272cfafbc35423e1678a7f8d85
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
