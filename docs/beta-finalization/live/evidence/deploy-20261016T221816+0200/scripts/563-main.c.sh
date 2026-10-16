#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-dialer/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-dialer/main.c
# previous-hash: 369af2f74288a042d85d80981b9ad14560a25202178c623d31366eccfd464a24
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-dialer/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-dialer/main.c ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-dialer/main.c /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-staged
printf '%s  %s\n' 369af2f74288a042d85d80981b9ad14560a25202178c623d31366eccfd464a24 /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-dialer/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-dialer/main.c | grep -q 369af2f74288a042d85d80981b9ad14560a25202178c623d31366eccfd464a24
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-dialer/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-dialer/main.c; true; fi
