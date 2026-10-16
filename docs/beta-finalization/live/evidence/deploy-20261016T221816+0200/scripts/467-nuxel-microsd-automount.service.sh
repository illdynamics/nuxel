#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/systemd/system/nuxel-microsd-automount.service (service: None, risk: medium)
# staged source: configs/nuxel/modem/nuxel-microsd-automount.service
# previous-hash: 0a6411effa2e587cd51980e1303cc9e8a67434406418d2a3325719769a541120
set -eu
mkdir -p "$(dirname /etc/systemd/system/nuxel-microsd-automount.service)"
if [ -e /etc/systemd/system/nuxel-microsd-automount.service ]; then cp -a /etc/systemd/system/nuxel-microsd-automount.service /etc/systemd/system/nuxel-microsd-automount.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-microsd-automount.service.nuxel-staged
printf '%s  %s\n' 0a6411effa2e587cd51980e1303cc9e8a67434406418d2a3325719769a541120 /etc/systemd/system/nuxel-microsd-automount.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-microsd-automount.service.nuxel-staged /etc/systemd/system/nuxel-microsd-automount.service
sha256sum /etc/systemd/system/nuxel-microsd-automount.service | grep -q 0a6411effa2e587cd51980e1303cc9e8a67434406418d2a3325719769a541120
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/systemd/system/nuxel-microsd-automount.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-microsd-automount.service.nuxel-rollback /etc/systemd/system/nuxel-microsd-automount.service; true; fi
