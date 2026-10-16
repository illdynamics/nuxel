#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/capabilities/connectivity-time-audio-buttons.json (service: None, risk: medium)
# staged source: configs/nuxel/capabilities/connectivity-time-audio-buttons.json
# previous-hash: 5070421858a3ee61014390c365e31afaa2727ff96a89e4c82f32d55d82fb96e2
set -eu
mkdir -p "$(dirname /etc/nuxel/capabilities/connectivity-time-audio-buttons.json)"
if [ -e /etc/nuxel/capabilities/connectivity-time-audio-buttons.json ]; then cp -a /etc/nuxel/capabilities/connectivity-time-audio-buttons.json /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-rollback; fi
test -f /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-staged
printf '%s  %s\n' 5070421858a3ee61014390c365e31afaa2727ff96a89e4c82f32d55d82fb96e2 /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-staged /etc/nuxel/capabilities/connectivity-time-audio-buttons.json
sha256sum /etc/nuxel/capabilities/connectivity-time-audio-buttons.json | grep -q 5070421858a3ee61014390c365e31afaa2727ff96a89e4c82f32d55d82fb96e2
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-rollback ]; then cp -a /etc/nuxel/capabilities/connectivity-time-audio-buttons.json.nuxel-rollback /etc/nuxel/capabilities/connectivity-time-audio-buttons.json; true; fi
