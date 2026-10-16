#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-sensors-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-sensors-diag.sh
# previous-hash: 3e5870abe2f4b80fa82a835e83d6a997bdd09ec3bc0b5f2d5d7819703b8f1c22
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-sensors-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-sensors-diag.sh.nuxel-rollback /usr/local/bin/nuxel-sensors-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-sensors-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-sensors-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-sensors-diag.sh)"
if [ -e /usr/local/bin/nuxel-sensors-diag.sh ] && [ ! -e /usr/local/bin/nuxel-sensors-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-sensors-diag.sh /usr/local/bin/nuxel-sensors-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-sensors-diag.sh.nuxel-staged
printf '%s  %s\n' 3e5870abe2f4b80fa82a835e83d6a997bdd09ec3bc0b5f2d5d7819703b8f1c22 /usr/local/bin/nuxel-sensors-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-sensors-diag.sh.nuxel-staged /usr/local/bin/nuxel-sensors-diag.sh
sha256sum /usr/local/bin/nuxel-sensors-diag.sh | grep -q 3e5870abe2f4b80fa82a835e83d6a997bdd09ec3bc0b5f2d5d7819703b8f1c22
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
