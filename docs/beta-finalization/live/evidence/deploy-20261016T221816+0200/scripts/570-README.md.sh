#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-phone-data/README.md
# previous-hash: 2d8f846c527cc03ad8d13b1f2b5ba6ab6a444d3336d522dd0ae62a5a8880605a
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-staged
printf '%s  %s\n' 2d8f846c527cc03ad8d13b1f2b5ba6ab6a444d3336d522dd0ae62a5a8880605a /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md
sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md | grep -q 2d8f846c527cc03ad8d13b1f2b5ba6ab6a444d3336d522dd0ae62a5a8880605a
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md; true; fi
