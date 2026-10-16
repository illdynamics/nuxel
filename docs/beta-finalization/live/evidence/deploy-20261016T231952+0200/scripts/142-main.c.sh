#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-permissions/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-permissions/main.c
# previous-hash: 6ae1b52320ea8d6f289c0657913026c08929e65aa9bebdb3e53263af8b5ed114
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-permissions/main.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-permissions/main.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-permissions/main.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-permissions/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-permissions/main.c ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-permissions/main.c /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-staged
printf '%s  %s\n' 6ae1b52320ea8d6f289c0657913026c08929e65aa9bebdb3e53263af8b5ed114 /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-permissions/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-permissions/main.c | grep -q 6ae1b52320ea8d6f289c0657913026c08929e65aa9bebdb3e53263af8b5ed114
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
