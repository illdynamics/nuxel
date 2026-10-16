#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf (service: None, risk: medium)
# staged source: configs/nuxel/bluetooth/main.conf.d/60-nuxel.conf
# previous-hash: 3497a02e5145854e319754f82d03ee2799231f5abb7d1db6d83f5d415cc14112
set -eu
mkdir -p "$(dirname /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf)"
if [ -e /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf ]; then cp -a /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-rollback; fi
test -f /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-staged
printf '%s  %s\n' 3497a02e5145854e319754f82d03ee2799231f5abb7d1db6d83f5d415cc14112 /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-staged /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf
sha256sum /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf | grep -q 3497a02e5145854e319754f82d03ee2799231f5abb7d1db6d83f5d415cc14112
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-rollback ]; then cp -a /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf.nuxel-rollback /etc/nuxel/bluetooth/main.conf.d/60-nuxel.conf; true; fi
