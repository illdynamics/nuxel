#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/README-cross.md (service: None, risk: medium)
# staged source: shell/nuxel-shell/README-cross.md
# previous-hash: 1db80fcf38c00249e64f440d611d7e13ebf150240911f9aafc1f633005b10e2c
set -eu
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/README-cross.md)"
if [ -e /usr/lib/nuxel/src/shell/README-cross.md ]; then cp -a /usr/lib/nuxel/src/shell/README-cross.md /usr/lib/nuxel/src/shell/README-cross.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/README-cross.md.nuxel-staged
printf '%s  %s\n' 1db80fcf38c00249e64f440d611d7e13ebf150240911f9aafc1f633005b10e2c /usr/lib/nuxel/src/shell/README-cross.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/README-cross.md.nuxel-staged /usr/lib/nuxel/src/shell/README-cross.md
sha256sum /usr/lib/nuxel/src/shell/README-cross.md | grep -q 1db80fcf38c00249e64f440d611d7e13ebf150240911f9aafc1f633005b10e2c
systemctl daemon-reload
systemctl daemon-reload
test -s /usr/lib/nuxel/nuxel-permissions/nuxel-permd.py && test -s /usr/lib/nuxel/nuxel-permissions/capabilities.json && test -x /usr/local/bin/nuxel-home-kiosk && test -s /usr/local/bin/nuxel-privacy-tor-control.py
systemctl daemon-reload
# rollback (run only if the health check above failed)
if [ -e /usr/lib/nuxel/src/shell/README-cross.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/README-cross.md.nuxel-rollback /usr/lib/nuxel/src/shell/README-cross.md; true; fi
