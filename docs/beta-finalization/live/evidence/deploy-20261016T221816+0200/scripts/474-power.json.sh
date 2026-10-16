#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/power/power.json (service: None, risk: medium)
# staged source: configs/nuxel/power/power.json
# previous-hash: 23a9dfedaf1c3f61ce11b2843e4533382161fa10caf00bfa616a4755a733c0a0
set -eu
mkdir -p "$(dirname /etc/nuxel/power/power.json)"
if [ -e /etc/nuxel/power/power.json ]; then cp -a /etc/nuxel/power/power.json /etc/nuxel/power/power.json.nuxel-rollback; fi
test -f /etc/nuxel/power/power.json.nuxel-staged
printf '%s  %s\n' 23a9dfedaf1c3f61ce11b2843e4533382161fa10caf00bfa616a4755a733c0a0 /etc/nuxel/power/power.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/power/power.json.nuxel-staged /etc/nuxel/power/power.json
sha256sum /etc/nuxel/power/power.json | grep -q 23a9dfedaf1c3f61ce11b2843e4533382161fa10caf00bfa616a4755a733c0a0
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/power/power.json.nuxel-rollback ]; then cp -a /etc/nuxel/power/power.json.nuxel-rollback /etc/nuxel/power/power.json; true; fi
