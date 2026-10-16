#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/pwa-template.json (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/pwa-template.json
# previous-hash: 841a21d486d45a0935dda2e196811cbdf4853814ec8de173c91aaab0503432db
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/pwa-template.json)"
if [ -e /etc/nuxel/sandbox/profiles/pwa-template.json ]; then cp -a /etc/nuxel/sandbox/profiles/pwa-template.json /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-staged
printf '%s  %s\n' 841a21d486d45a0935dda2e196811cbdf4853814ec8de173c91aaab0503432db /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-staged /etc/nuxel/sandbox/profiles/pwa-template.json
sha256sum /etc/nuxel/sandbox/profiles/pwa-template.json | grep -q 841a21d486d45a0935dda2e196811cbdf4853814ec8de173c91aaab0503432db
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/pwa-template.json.nuxel-rollback /etc/nuxel/sandbox/profiles/pwa-template.json; true; fi
