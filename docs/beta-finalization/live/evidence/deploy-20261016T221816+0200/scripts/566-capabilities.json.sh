#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/nuxel-permissions/capabilities.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-permissions/capabilities.json
# previous-hash: fea064b1d3bd05e1813d70447cd5f34d9bd900b8b599d665f85d27cef25a87e3
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/nuxel-permissions/capabilities.json)"
if [ -e /usr/lib/nuxel/nuxel-permissions/capabilities.json ]; then cp -a /usr/lib/nuxel/nuxel-permissions/capabilities.json /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-rollback; fi
test -f /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-staged
printf '%s  %s\n' fea064b1d3bd05e1813d70447cd5f34d9bd900b8b599d665f85d27cef25a87e3 /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-staged /usr/lib/nuxel/nuxel-permissions/capabilities.json
sha256sum /usr/lib/nuxel/nuxel-permissions/capabilities.json | grep -q fea064b1d3bd05e1813d70447cd5f34d9bd900b8b599d665f85d27cef25a87e3
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-rollback ]; then cp -a /usr/lib/nuxel/nuxel-permissions/capabilities.json.nuxel-rollback /usr/lib/nuxel/nuxel-permissions/capabilities.json; true; fi
