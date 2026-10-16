#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-permissions/nuxel-permd.py
# previous-hash: 7546928ea435af6236efd9e05a04984a80e775fe939e23f6edc808ba1ab5f351
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py)"
if [ -e /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py ]; then cp -a /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-staged
printf '%s  %s\n' 7546928ea435af6236efd9e05a04984a80e775fe939e23f6edc808ba1ab5f351 /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-staged /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py
sha256sum /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py | grep -q 7546928ea435af6236efd9e05a04984a80e775fe939e23f6edc808ba1ab5f351
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py.nuxel-rollback /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py; true; fi
