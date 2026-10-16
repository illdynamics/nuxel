#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-messages.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-messages.json
# previous-hash: 7ba696fb1f60138b0d83928e3fb8fd1eed3637529111b6ca4d491f05fa734ed4
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-messages.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-messages.json ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-messages.json /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-staged
printf '%s  %s\n' 7ba696fb1f60138b0d83928e3fb8fd1eed3637529111b6ca4d491f05fa734ed4 /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-messages.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-messages.json | grep -q 7ba696fb1f60138b0d83928e3fb8fd1eed3637529111b6ca4d491f05fa734ed4
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-messages.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-messages.json; true; fi
