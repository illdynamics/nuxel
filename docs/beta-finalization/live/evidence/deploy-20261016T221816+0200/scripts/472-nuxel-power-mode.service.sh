#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-power-mode.service (service: None, risk: medium)
# staged source: configs/nuxel/power/nuxel-power-mode.service
# previous-hash: 96ced4aa23e54be09a67fc5d2827f2b18254cd7a64935bdea995733bcb30ff92
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-power-mode.service)"
if [ -e /etc/systemd/system/nuxel-power-mode.service ]; then cp -a /etc/systemd/system/nuxel-power-mode.service /etc/systemd/system/nuxel-power-mode.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-power-mode.service.nuxel-staged
printf '%s  %s\n' 96ced4aa23e54be09a67fc5d2827f2b18254cd7a64935bdea995733bcb30ff92 /etc/systemd/system/nuxel-power-mode.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-power-mode.service.nuxel-staged /etc/systemd/system/nuxel-power-mode.service
sha256sum /etc/systemd/system/nuxel-power-mode.service | grep -q 96ced4aa23e54be09a67fc5d2827f2b18254cd7a64935bdea995733bcb30ff92
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-power-mode.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-power-mode.service.nuxel-rollback /etc/systemd/system/nuxel-power-mode.service; true; fi
