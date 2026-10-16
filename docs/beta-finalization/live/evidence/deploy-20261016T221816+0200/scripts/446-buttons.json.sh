#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/input/buttons.json (service: None, risk: medium)
# staged source: configs/nuxel/buttons.json
# previous-hash: 6e9994c054d8e983bdf0fe66a476106ad9036e21286aafb5871d778193e5ff25
set -eu
mkdir -p "$(dirname /etc/nuxel/input/buttons.json)"
if [ -e /etc/nuxel/input/buttons.json ]; then cp -a /etc/nuxel/input/buttons.json /etc/nuxel/input/buttons.json.nuxel-rollback; fi
test -f /etc/nuxel/input/buttons.json.nuxel-staged
printf '%s  %s\n' 6e9994c054d8e983bdf0fe66a476106ad9036e21286aafb5871d778193e5ff25 /etc/nuxel/input/buttons.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/input/buttons.json.nuxel-staged /etc/nuxel/input/buttons.json
sha256sum /etc/nuxel/input/buttons.json | grep -q 6e9994c054d8e983bdf0fe66a476106ad9036e21286aafb5871d778193e5ff25
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/input/buttons.json.nuxel-rollback ]; then cp -a /etc/nuxel/input/buttons.json.nuxel-rollback /etc/nuxel/input/buttons.json; true; fi
