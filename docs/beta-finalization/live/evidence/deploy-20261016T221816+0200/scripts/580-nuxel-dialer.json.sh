#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-dialer.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-dialer.json
# previous-hash: c118f58a9636081896a79fb8a9aa9a026fedbdc3a25ff4b51ae4518bd9f13ea8
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-dialer.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-dialer.json ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-dialer.json /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-staged
printf '%s  %s\n' c118f58a9636081896a79fb8a9aa9a026fedbdc3a25ff4b51ae4518bd9f13ea8 /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-dialer.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-dialer.json | grep -q c118f58a9636081896a79fb8a9aa9a026fedbdc3a25ff4b51ae4518bd9f13ea8
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-dialer.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-dialer.json; true; fi
