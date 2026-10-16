#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-settings.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-settings.json
# previous-hash: 1bfbb71af58b0ea63f0651b911e582b120a8ebdea534a83b5352170e4ce230ed
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-settings.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-settings.json ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-settings.json /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-staged
printf '%s  %s\n' 1bfbb71af58b0ea63f0651b911e582b120a8ebdea534a83b5352170e4ce230ed /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-settings.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-settings.json | grep -q 1bfbb71af58b0ea63f0651b911e582b120a8ebdea534a83b5352170e4ce230ed
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-settings.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-settings.json; true; fi
