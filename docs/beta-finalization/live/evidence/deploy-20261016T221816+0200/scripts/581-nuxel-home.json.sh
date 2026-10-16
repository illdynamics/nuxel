#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-home.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-home.json
# previous-hash: 4da28388b2062e13f1db6823350b55064654cc579bfd409b7ef3049a57dfa019
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-home.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-home.json ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-home.json /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-staged
printf '%s  %s\n' 4da28388b2062e13f1db6823350b55064654cc579bfd409b7ef3049a57dfa019 /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-home.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-home.json | grep -q 4da28388b2062e13f1db6823350b55064654cc579bfd409b7ef3049a57dfa019
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-home.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-home.json; true; fi
