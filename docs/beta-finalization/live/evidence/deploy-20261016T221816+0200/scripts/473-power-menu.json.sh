#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/power/power-menu.json (service: None, risk: medium)
# staged source: configs/nuxel/power/power-menu.json
# previous-hash: 8c640abd6acd1db701c4a37324de67eb246f98c8e4181e39a4395e98e8a8eb24
set -eu
mkdir -p "$(dirname /etc/nuxel/power/power-menu.json)"
if [ -e /etc/nuxel/power/power-menu.json ]; then cp -a /etc/nuxel/power/power-menu.json /etc/nuxel/power/power-menu.json.nuxel-rollback; fi
test -f /etc/nuxel/power/power-menu.json.nuxel-staged
printf '%s  %s\n' 8c640abd6acd1db701c4a37324de67eb246f98c8e4181e39a4395e98e8a8eb24 /etc/nuxel/power/power-menu.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/power/power-menu.json.nuxel-staged /etc/nuxel/power/power-menu.json
sha256sum /etc/nuxel/power/power-menu.json | grep -q 8c640abd6acd1db701c4a37324de67eb246f98c8e4181e39a4395e98e8a8eb24
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/power/power-menu.json.nuxel-rollback ]; then cp -a /etc/nuxel/power/power-menu.json.nuxel-rollback /etc/nuxel/power/power-menu.json; true; fi
