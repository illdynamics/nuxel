#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.c
# previous-hash: af0541c5e3e3da56e44d9347ed0dd1c3a6ddb84897795a3371b3f1f3c7396f93
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-staged
printf '%s  %s\n' af0541c5e3e3da56e44d9347ed0dd1c3a6ddb84897795a3371b3f1f3c7396f93 /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c | grep -q af0541c5e3e3da56e44d9347ed0dd1c3a6ddb84897795a3371b3f1f3c7396f93
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c; true; fi
