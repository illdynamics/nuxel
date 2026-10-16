#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-permissions/nuxel-permd.py
# previous-hash: 7546928ea435af6236efd9e05a04984a80e775fe939e23f6edc808ba1ab5f351
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-rollback /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py)"
if [ -e /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py ] && [ ! -e /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-staged
printf '%s  %s\n' 7546928ea435af6236efd9e05a04984a80e775fe939e23f6edc808ba1ab5f351 /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-staged /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py
sha256sum /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py | grep -q 7546928ea435af6236efd9e05a04984a80e775fe939e23f6edc808ba1ab5f351
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
