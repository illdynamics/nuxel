#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/README-cross.md (service: None, risk: medium)
# staged source: shell/nuxel-shell/README-cross.md
# previous-hash: 1db80fcf38c00249e64f440d611d7e13ebf150240911f9aafc1f633005b10e2c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/README-cross.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/README-cross.md.nuxel-rollback /usr/lib/nuxel/src/shell/README-cross.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/README-cross.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/README-cross.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/README-cross.md)"
if [ -e /usr/lib/nuxel/src/shell/README-cross.md ] && [ ! -e /usr/lib/nuxel/src/shell/README-cross.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/README-cross.md /usr/lib/nuxel/src/shell/README-cross.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/README-cross.md.nuxel-staged
printf '%s  %s\n' 1db80fcf38c00249e64f440d611d7e13ebf150240911f9aafc1f633005b10e2c /usr/lib/nuxel/src/shell/README-cross.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/README-cross.md.nuxel-staged /usr/lib/nuxel/src/shell/README-cross.md
sha256sum /usr/lib/nuxel/src/shell/README-cross.md | grep -q 1db80fcf38c00249e64f440d611d7e13ebf150240911f9aafc1f633005b10e2c
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
