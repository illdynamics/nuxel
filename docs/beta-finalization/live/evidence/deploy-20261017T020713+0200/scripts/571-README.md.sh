#!/bin/sh
# native shell applications (sources, units, profiles) -> /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md (service: None, risk: medium)
# staged source: shell/nuxel-shell/nuxel-phone-data/README.md
# previous-hash: 2d8f846c527cc03ad8d13b1f2b5ba6ab6a444d3336d522dd0ae62a5a8880605a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-rollback /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md)"
if [ -e /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md ] && [ ! -e /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-rollback ]; then cp -a /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-rollback; fi
test -f /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-staged
printf '%s  %s\n' 2d8f846c527cc03ad8d13b1f2b5ba6ab6a444d3336d522dd0ae62a5a8880605a /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md.nuxel-staged /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md
sha256sum /usr/lib/nuxel/src/shell/nuxel-phone-data/README.md | grep -q 2d8f846c527cc03ad8d13b1f2b5ba6ab6a444d3336d522dd0ae62a5a8880605a
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
