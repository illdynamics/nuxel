#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/leds/README.md (service: None, risk: medium)
# staged source: configs/nuxel/leds/README.md
# previous-hash: 6dce3fa5bc6ae6ef1975c3f770072292e00487b9cb57e8da6275981019943ac6
set -eu
mkdir -p "$(dirname /etc/nuxel/leds/README.md)"
if [ -e /etc/nuxel/leds/README.md ]; then cp -a /etc/nuxel/leds/README.md /etc/nuxel/leds/README.md.nuxel-rollback; fi
test -f /etc/nuxel/leds/README.md.nuxel-staged
printf '%s  %s\n' 6dce3fa5bc6ae6ef1975c3f770072292e00487b9cb57e8da6275981019943ac6 /etc/nuxel/leds/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/leds/README.md.nuxel-staged /etc/nuxel/leds/README.md
sha256sum /etc/nuxel/leds/README.md | grep -q 6dce3fa5bc6ae6ef1975c3f770072292e00487b9cb57e8da6275981019943ac6
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/leds/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/leds/README.md.nuxel-rollback /etc/nuxel/leds/README.md; true; fi
