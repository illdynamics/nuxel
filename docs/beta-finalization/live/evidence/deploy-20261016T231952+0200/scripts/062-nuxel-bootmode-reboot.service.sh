#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-bootmode-reboot.service (service: None, risk: medium)
# staged source: configs/nuxel/touch/nuxel-bootmode-reboot.service
# previous-hash: d7f4b5ee7a989510b5523f2a5e0f4f667388840fea5ec11f904bbf4cecb68575
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bootmode-reboot.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bootmode-reboot.service.nuxel-rollback /etc/systemd/system/nuxel-bootmode-reboot.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-bootmode-reboot.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bootmode-reboot.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bootmode-reboot.service)"
if [ -e /etc/systemd/system/nuxel-bootmode-reboot.service ] && [ ! -e /etc/systemd/system/nuxel-bootmode-reboot.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bootmode-reboot.service /etc/systemd/system/nuxel-bootmode-reboot.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-bootmode-reboot.service.nuxel-staged
printf '%s  %s\n' d7f4b5ee7a989510b5523f2a5e0f4f667388840fea5ec11f904bbf4cecb68575 /etc/systemd/system/nuxel-bootmode-reboot.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bootmode-reboot.service.nuxel-staged /etc/systemd/system/nuxel-bootmode-reboot.service
sha256sum /etc/systemd/system/nuxel-bootmode-reboot.service | grep -q d7f4b5ee7a989510b5523f2a5e0f4f667388840fea5ec11f904bbf4cecb68575
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
