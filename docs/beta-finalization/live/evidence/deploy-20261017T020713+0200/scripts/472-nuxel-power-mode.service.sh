#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-power-mode.service (service: None, risk: medium)
# staged source: configs/nuxel/power/nuxel-power-mode.service
# previous-hash: 96ced4aa23e54be09a67fc5d2827f2b18254cd7a64935bdea995733bcb30ff92
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-power-mode.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-power-mode.service.nuxel-rollback /etc/systemd/system/nuxel-power-mode.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-power-mode.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-power-mode.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-power-mode.service)"
if [ -e /etc/systemd/system/nuxel-power-mode.service ] && [ ! -e /etc/systemd/system/nuxel-power-mode.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-power-mode.service /etc/systemd/system/nuxel-power-mode.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-power-mode.service.nuxel-staged
printf '%s  %s\n' 96ced4aa23e54be09a67fc5d2827f2b18254cd7a64935bdea995733bcb30ff92 /etc/systemd/system/nuxel-power-mode.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-power-mode.service.nuxel-staged /etc/systemd/system/nuxel-power-mode.service
sha256sum /etc/systemd/system/nuxel-power-mode.service | grep -q 96ced4aa23e54be09a67fc5d2827f2b18254cd7a64935bdea995733bcb30ff92
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
