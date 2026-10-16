#!/bin/sh
# audio / network runtime config -> /etc/nuxel/app-registry/app_registry.json (service: None, risk: medium)
# staged source: configs/nuxel/app-registry/app_registry.json
# previous-hash: 984106329ad0fce60b4974aa601946e7ccf9e6dcc7422a70289a835c813b0f2b
set -eu
mkdir -p "$(dirname /etc/nuxel/app-registry/app_registry.json)"
if [ -e /etc/nuxel/app-registry/app_registry.json ]; then cp -a /etc/nuxel/app-registry/app_registry.json /etc/nuxel/app-registry/app_registry.json.nuxel-rollback; fi
test -f /etc/nuxel/app-registry/app_registry.json.nuxel-staged
printf '%s  %s\n' 984106329ad0fce60b4974aa601946e7ccf9e6dcc7422a70289a835c813b0f2b /etc/nuxel/app-registry/app_registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/app-registry/app_registry.json.nuxel-staged /etc/nuxel/app-registry/app_registry.json
sha256sum /etc/nuxel/app-registry/app_registry.json | grep -q 984106329ad0fce60b4974aa601946e7ccf9e6dcc7422a70289a835c813b0f2b
grep -q beyond-madera /proc/asound/cards
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/app-registry/app_registry.json.nuxel-rollback ]; then cp -a /etc/nuxel/app-registry/app_registry.json.nuxel-rollback /etc/nuxel/app-registry/app_registry.json; true; fi
