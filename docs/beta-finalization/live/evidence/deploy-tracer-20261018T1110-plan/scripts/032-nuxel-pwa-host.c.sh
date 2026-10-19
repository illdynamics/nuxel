#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/lib/nuxel/src/a33/nuxel-pwa-host.c (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-pwa-host.c
# previous-hash: 8351e4b3932f9be4bf2d526c653dd7184d39824b5ec65fb5f1022518e917e171
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-rollback /usr/lib/nuxel/src/a33/nuxel-pwa-host.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/a33/nuxel-pwa-host.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/a33/nuxel-pwa-host.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/a33/nuxel-pwa-host.c)"
if [ -e /usr/lib/nuxel/src/a33/nuxel-pwa-host.c ] && [ ! -e /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/a33/nuxel-pwa-host.c /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-staged
printf '%s  %s\n' 8351e4b3932f9be4bf2d526c653dd7184d39824b5ec65fb5f1022518e917e171 /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/a33/nuxel-pwa-host.c.nuxel-staged /usr/lib/nuxel/src/a33/nuxel-pwa-host.c
sha256sum /usr/lib/nuxel/src/a33/nuxel-pwa-host.c | grep -q 8351e4b3932f9be4bf2d526c653dd7184d39824b5ec65fb5f1022518e917e171
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
