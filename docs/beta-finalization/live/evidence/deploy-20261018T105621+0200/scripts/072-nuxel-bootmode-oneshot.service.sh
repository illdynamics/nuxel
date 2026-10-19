#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-bootmode-oneshot.service (service: None, risk: medium)
# staged source: services/nuxel-session/systemd/nuxel-bootmode-oneshot.service
# previous-hash: 63831fc1cd01b8d1dc40ffd88fca9c84f55349ef0f7ab8065f3db2fef20a32e0
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bootmode-oneshot.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bootmode-oneshot.service.nuxel-rollback /etc/systemd/system/nuxel-bootmode-oneshot.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-bootmode-oneshot.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bootmode-oneshot.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bootmode-oneshot.service)"
if [ -e /etc/systemd/system/nuxel-bootmode-oneshot.service ] && [ ! -e /etc/systemd/system/nuxel-bootmode-oneshot.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bootmode-oneshot.service /etc/systemd/system/nuxel-bootmode-oneshot.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-bootmode-oneshot.service.nuxel-staged
printf '%s  %s\n' 63831fc1cd01b8d1dc40ffd88fca9c84f55349ef0f7ab8065f3db2fef20a32e0 /etc/systemd/system/nuxel-bootmode-oneshot.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bootmode-oneshot.service.nuxel-staged /etc/systemd/system/nuxel-bootmode-oneshot.service
sha256sum /etc/systemd/system/nuxel-bootmode-oneshot.service | grep -q 63831fc1cd01b8d1dc40ffd88fca9c84f55349ef0f7ab8065f3db2fef20a32e0
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
