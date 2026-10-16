#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/keyboard/keyboard.schema.json (service: None, risk: medium)
# staged source: configs/nuxel/keyboard/keyboard.schema.json
# previous-hash: 6e7776b02bd16883e5dc4afdc3b0ce432d71734c68f0613995b5305fc410d561
set -eu
mkdir -p "$(dirname /etc/nuxel/keyboard/keyboard.schema.json)"
if [ -e /etc/nuxel/keyboard/keyboard.schema.json ]; then cp -a /etc/nuxel/keyboard/keyboard.schema.json /etc/nuxel/keyboard/keyboard.schema.json.nuxel-rollback; fi
test -f /etc/nuxel/keyboard/keyboard.schema.json.nuxel-staged
printf '%s  %s\n' 6e7776b02bd16883e5dc4afdc3b0ce432d71734c68f0613995b5305fc410d561 /etc/nuxel/keyboard/keyboard.schema.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/keyboard/keyboard.schema.json.nuxel-staged /etc/nuxel/keyboard/keyboard.schema.json
sha256sum /etc/nuxel/keyboard/keyboard.schema.json | grep -q 6e7776b02bd16883e5dc4afdc3b0ce432d71734c68f0613995b5305fc410d561
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/keyboard/keyboard.schema.json.nuxel-rollback ]; then cp -a /etc/nuxel/keyboard/keyboard.schema.json.nuxel-rollback /etc/nuxel/keyboard/keyboard.schema.json; true; fi
