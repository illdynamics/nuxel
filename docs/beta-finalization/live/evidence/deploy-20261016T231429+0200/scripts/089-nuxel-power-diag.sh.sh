#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-power-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-power-diag.sh
# previous-hash: 0b5aaaf3eedf1415634c3bd976cf69a372656876bd9cdf91fa1eac7162815479
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-power-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-power-diag.sh.nuxel-rollback /usr/local/bin/nuxel-power-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-power-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-power-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-power-diag.sh)"
if [ -e /usr/local/bin/nuxel-power-diag.sh ] && [ ! -e /usr/local/bin/nuxel-power-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-power-diag.sh /usr/local/bin/nuxel-power-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-power-diag.sh.nuxel-staged
printf '%s  %s\n' 0b5aaaf3eedf1415634c3bd976cf69a372656876bd9cdf91fa1eac7162815479 /usr/local/bin/nuxel-power-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-power-diag.sh.nuxel-staged /usr/local/bin/nuxel-power-diag.sh
sha256sum /usr/local/bin/nuxel-power-diag.sh | grep -q 0b5aaaf3eedf1415634c3bd976cf69a372656876bd9cdf91fa1eac7162815479
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
