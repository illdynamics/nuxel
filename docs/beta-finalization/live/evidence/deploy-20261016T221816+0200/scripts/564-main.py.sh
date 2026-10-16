#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-firstboot/main.py
# previous-hash: ae85417b386249ca49def4a63eaf298fee11d6e5e4070be1b4233b76b488e88b
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-staged
printf '%s  %s\n' ae85417b386249ca49def4a63eaf298fee11d6e5e4070be1b4233b76b488e88b /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py
sha256sum /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py | grep -q ae85417b386249ca49def4a63eaf298fee11d6e5e4070be1b4233b76b488e88b
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-firstboot/main.py; true; fi
