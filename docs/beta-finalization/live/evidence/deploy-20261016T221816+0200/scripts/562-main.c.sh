#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-contacts/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-contacts/main.c
# previous-hash: 0af4c6e4c5b8c63565ea7465d72580ec4d4bdfb6bf1932e3464cb4de92724ca3
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-contacts/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-contacts/main.c ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-contacts/main.c /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-staged
printf '%s  %s\n' 0af4c6e4c5b8c63565ea7465d72580ec4d4bdfb6bf1932e3464cb4de92724ca3 /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-contacts/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-contacts/main.c | grep -q 0af4c6e4c5b8c63565ea7465d72580ec4d4bdfb6bf1932e3464cb4de92724ca3
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-contacts/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-contacts/main.c; true; fi
