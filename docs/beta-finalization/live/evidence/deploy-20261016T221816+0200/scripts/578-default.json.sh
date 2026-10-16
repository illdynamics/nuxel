#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/default.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/default.json
# previous-hash: c5749e7fe4ce28c1a4031062b66a8bbf2984ea0b6d9f91f49edf474a234656a0
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/default.json)"
if [ -e /etc/nuxel/sandbox/profiles/default.json ]; then cp -a /etc/nuxel/sandbox/profiles/default.json /etc/nuxel/sandbox/profiles/default.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/default.json.nuxel-staged
printf '%s  %s\n' c5749e7fe4ce28c1a4031062b66a8bbf2984ea0b6d9f91f49edf474a234656a0 /etc/nuxel/sandbox/profiles/default.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/default.json.nuxel-staged /etc/nuxel/sandbox/profiles/default.json
sha256sum /etc/nuxel/sandbox/profiles/default.json | grep -q c5749e7fe4ce28c1a4031062b66a8bbf2984ea0b6d9f91f49edf474a234656a0
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/default.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/default.json.nuxel-rollback /etc/nuxel/sandbox/profiles/default.json; true; fi
