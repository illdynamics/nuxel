#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-settings/main.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-settings/main.c
# previous-hash: 1147c53e781e3c031fecbd1fb492af4b7ff894f03345acb42a21bb4627270bbb
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-settings/main.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-settings/main.c ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-settings/main.c /usr/lib/nuxel/src/shell/nuxel-settings/main.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-settings/main.c.nuxel-staged
printf '%s  %s\n' 1147c53e781e3c031fecbd1fb492af4b7ff894f03345acb42a21bb4627270bbb /usr/lib/nuxel/src/shell/nuxel-settings/main.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-settings/main.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-settings/main.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-settings/main.c | grep -q 1147c53e781e3c031fecbd1fb492af4b7ff894f03345acb42a21bb4627270bbb
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-settings/main.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-settings/main.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-settings/main.c; true; fi
