#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/nuxel-privacy.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/nuxel-privacy.json
# previous-hash: 348302a4b284a39872eee81df904660eafb49fcd7476c9f9a8731f430e31a0b2
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/nuxel-privacy.json)"
if [ -e /etc/nuxel/sandbox/profiles/nuxel-privacy.json ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-privacy.json /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-staged
printf '%s  %s\n' 348302a4b284a39872eee81df904660eafb49fcd7476c9f9a8731f430e31a0b2 /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-staged /etc/nuxel/sandbox/profiles/nuxel-privacy.json
sha256sum /etc/nuxel/sandbox/profiles/nuxel-privacy.json | grep -q 348302a4b284a39872eee81df904660eafb49fcd7476c9f9a8731f430e31a0b2
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/nuxel-privacy.json.nuxel-rollback /etc/nuxel/sandbox/profiles/nuxel-privacy.json; true; fi
