#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/keyboard/keyboard.json (service: None, risk: medium)
# staged source: configs/nuxel/keyboard/keyboard.json
# previous-hash: 9cef7e92b8ba4d64b2e6d8e70fc10706e9fc0d899930925f6e47032504fd55d2
set -eu
mkdir -p "$(dirname /etc/nuxel/keyboard/keyboard.json)"
if [ -e /etc/nuxel/keyboard/keyboard.json ]; then cp -a /etc/nuxel/keyboard/keyboard.json /etc/nuxel/keyboard/keyboard.json.nuxel-rollback; fi
test -f /etc/nuxel/keyboard/keyboard.json.nuxel-staged
printf '%s  %s\n' 9cef7e92b8ba4d64b2e6d8e70fc10706e9fc0d899930925f6e47032504fd55d2 /etc/nuxel/keyboard/keyboard.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/keyboard/keyboard.json.nuxel-staged /etc/nuxel/keyboard/keyboard.json
sha256sum /etc/nuxel/keyboard/keyboard.json | grep -q 9cef7e92b8ba4d64b2e6d8e70fc10706e9fc0d899930925f6e47032504fd55d2
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/keyboard/keyboard.json.nuxel-rollback ]; then cp -a /etc/nuxel/keyboard/keyboard.json.nuxel-rollback /etc/nuxel/keyboard/keyboard.json; true; fi
