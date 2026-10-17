#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/systemd/system/nuxel-permd.service (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-permissions/systemd/nuxel-permd.service
# previous-hash: 952976c624e5cfbc9e2e19d2349919f750f9390d7ebc3f31d9195537baca817c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-permd.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-permd.service.nuxel-rollback /etc/systemd/system/nuxel-permd.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-permd.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-permd.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-permd.service)"
if [ -e /etc/systemd/system/nuxel-permd.service ] && [ ! -e /etc/systemd/system/nuxel-permd.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-permd.service /etc/systemd/system/nuxel-permd.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-permd.service.nuxel-staged
printf '%s  %s\n' 952976c624e5cfbc9e2e19d2349919f750f9390d7ebc3f31d9195537baca817c /etc/systemd/system/nuxel-permd.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-permd.service.nuxel-staged /etc/systemd/system/nuxel-permd.service
sha256sum /etc/systemd/system/nuxel-permd.service | grep -q 952976c624e5cfbc9e2e19d2349919f750f9390d7ebc3f31d9195537baca817c
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
