#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/bootmode/bootmode-guard.json (service: None, risk: medium)
# staged source: configs/nuxel/bootmode/bootmode-guard.json
# previous-hash: dd0028086831c7c857e1a10b4d033ccfb873efa40de3a6c7332174ea327b6ff9
set -eu
mkdir -p "$(dirname /etc/nuxel/bootmode/bootmode-guard.json)"
if [ -e /etc/nuxel/bootmode/bootmode-guard.json ]; then cp -a /etc/nuxel/bootmode/bootmode-guard.json /etc/nuxel/bootmode/bootmode-guard.json.nuxel-rollback; fi
test -f /etc/nuxel/bootmode/bootmode-guard.json.nuxel-staged
printf '%s  %s\n' dd0028086831c7c857e1a10b4d033ccfb873efa40de3a6c7332174ea327b6ff9 /etc/nuxel/bootmode/bootmode-guard.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bootmode/bootmode-guard.json.nuxel-staged /etc/nuxel/bootmode/bootmode-guard.json
sha256sum /etc/nuxel/bootmode/bootmode-guard.json | grep -q dd0028086831c7c857e1a10b4d033ccfb873efa40de3a6c7332174ea327b6ff9
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/bootmode/bootmode-guard.json.nuxel-rollback ]; then cp -a /etc/nuxel/bootmode/bootmode-guard.json.nuxel-rollback /etc/nuxel/bootmode/bootmode-guard.json; true; fi
