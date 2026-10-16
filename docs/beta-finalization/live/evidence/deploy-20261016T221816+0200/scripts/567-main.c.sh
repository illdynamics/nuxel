#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-permissions/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-permissions/main.c
# previous-hash: 6ae1b52320ea8d6f289c0657913026c08929e65aa9bebdb3e53263af8b5ed114
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-permissions/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-permissions/main.c ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-permissions/main.c /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-staged
printf '%s  %s\n' 6ae1b52320ea8d6f289c0657913026c08929e65aa9bebdb3e53263af8b5ed114 /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-permissions/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-permissions/main.c | grep -q 6ae1b52320ea8d6f289c0657913026c08929e65aa9bebdb3e53263af8b5ed114
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-permissions/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-permissions/main.c; true; fi
