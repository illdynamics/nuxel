#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-permissions.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-permissions.json
# previous-hash: 9ff3870314de94d83859d02a7521354c1268b4b3d90ebe3143ee400be4fa8b62
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-permissions.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-permissions.json ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-permissions.json /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-staged
printf '%s  %s\n' 9ff3870314de94d83859d02a7521354c1268b4b3d90ebe3143ee400be4fa8b62 /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-permissions.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-permissions.json | grep -q 9ff3870314de94d83859d02a7521354c1268b4b3d90ebe3143ee400be4fa8b62
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-permissions.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-permissions.json; true; fi
