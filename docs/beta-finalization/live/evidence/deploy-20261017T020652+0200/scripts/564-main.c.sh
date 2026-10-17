#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-dialer/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-dialer/main.c
# previous-hash: 369af2f74288a042d85d80981b9ad14560a25202178c623d31366eccfd464a24
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-dialer/main.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-dialer/main.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-dialer/main.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-dialer/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-dialer/main.c ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-dialer/main.c /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-staged
printf '%s  %s\n' 369af2f74288a042d85d80981b9ad14560a25202178c623d31366eccfd464a24 /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-dialer/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-dialer/main.c | grep -q 369af2f74288a042d85d80981b9ad14560a25202178c623d31366eccfd464a24
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
