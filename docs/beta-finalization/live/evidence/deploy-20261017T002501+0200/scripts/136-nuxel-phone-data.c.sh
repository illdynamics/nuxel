#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.c
# previous-hash: af0541c5e3e3da56e44d9347ed0dd1c3a6ddb84897795a3371b3f1f3c7396f93
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-staged
printf '%s  %s\n' af0541c5e3e3da56e44d9347ed0dd1c3a6ddb84897795a3371b3f1f3c7396f93 /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c
sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/nuxel-phone-data.c | grep -q af0541c5e3e3da56e44d9347ed0dd1c3a6ddb84897795a3371b3f1f3c7396f93
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
