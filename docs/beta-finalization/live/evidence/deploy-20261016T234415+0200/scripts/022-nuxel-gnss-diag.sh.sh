#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-gnss-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-gnss-diag.sh
# previous-hash: 76baf8fa9493bee5578be670068895b9b686be08bedf5a4c0f07c48f6860dbb6
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-gnss-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-gnss-diag.sh.nuxel-rollback /usr/local/bin/nuxel-gnss-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-gnss-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-gnss-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-gnss-diag.sh)"
if [ -e /usr/local/bin/nuxel-gnss-diag.sh ] && [ ! -e /usr/local/bin/nuxel-gnss-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-gnss-diag.sh /usr/local/bin/nuxel-gnss-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-gnss-diag.sh.nuxel-staged
printf '%s  %s\n' 76baf8fa9493bee5578be670068895b9b686be08bedf5a4c0f07c48f6860dbb6 /usr/local/bin/nuxel-gnss-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-gnss-diag.sh.nuxel-staged /usr/local/bin/nuxel-gnss-diag.sh
sha256sum /usr/local/bin/nuxel-gnss-diag.sh | grep -q 76baf8fa9493bee5578be670068895b9b686be08bedf5a4c0f07c48f6860dbb6
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
