#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/camera/camera.json (service: None, risk: medium)
# staged source: configs/nuxel/camera/camera.json
# previous-hash: bef369c250d90cf5a5fd8f26a8d3b8e6ee64b050c34b16c7491ecef9ce61fdca
set -eu
mkdir -p "$(dirname /etc/nuxel/camera/camera.json)"
if [ -e /etc/nuxel/camera/camera.json ]; then cp -a /etc/nuxel/camera/camera.json /etc/nuxel/camera/camera.json.nuxel-rollback; fi
test -f /etc/nuxel/camera/camera.json.nuxel-staged
printf '%s  %s\n' bef369c250d90cf5a5fd8f26a8d3b8e6ee64b050c34b16c7491ecef9ce61fdca /etc/nuxel/camera/camera.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/camera/camera.json.nuxel-staged /etc/nuxel/camera/camera.json
sha256sum /etc/nuxel/camera/camera.json | grep -q bef369c250d90cf5a5fd8f26a8d3b8e6ee64b050c34b16c7491ecef9ce61fdca
systemctl daemon-reload
systemctl daemon-reload
test -s /etc/nuxel/paths.conf && python3 -c "import json;json.load(open('/etc/nuxel/capabilities/hardware-subsystems.json'));json.load(open('/etc/nuxel/bootmode/bootmode-guard.json'))"
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/camera/camera.json.nuxel-rollback ]; then cp -a /etc/nuxel/camera/camera.json.nuxel-rollback /etc/nuxel/camera/camera.json; true; fi
