#!/bin/sh
# native shell applications (sources, units, profiles) -> /etc/nuxel/sandbox/profiles/README.md (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-sandbox/profiles/README.md
# previous-hash: d3493f90c7214eb83400b4e4262da122f6e9028b4997a5af55db14254370e173
set -eu
mkdir -p "$(dirname /etc/nuxel/sandbox/profiles/README.md)"
if [ -e /etc/nuxel/sandbox/profiles/README.md ]; then cp -a /etc/nuxel/sandbox/profiles/README.md /etc/nuxel/sandbox/profiles/README.md.nuxel-rollback; fi
test -f /etc/nuxel/sandbox/profiles/README.md.nuxel-staged
printf '%s  %s\n' d3493f90c7214eb83400b4e4262da122f6e9028b4997a5af55db14254370e173 /etc/nuxel/sandbox/profiles/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/sandbox/profiles/README.md.nuxel-staged /etc/nuxel/sandbox/profiles/README.md
sha256sum /etc/nuxel/sandbox/profiles/README.md | grep -q d3493f90c7214eb83400b4e4262da122f6e9028b4997a5af55db14254370e173
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /etc/nuxel/sandbox/profiles/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/sandbox/profiles/README.md.nuxel-rollback /etc/nuxel/sandbox/profiles/README.md; true; fi
