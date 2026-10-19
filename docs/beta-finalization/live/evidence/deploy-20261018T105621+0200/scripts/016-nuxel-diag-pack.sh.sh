#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-diag-pack.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-diag-pack.sh
# previous-hash: ecfc39e32783bd2803a14334395c3f3c165dd20b695dbde6f9df0bd1f2739e95
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-diag-pack.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-diag-pack.sh.nuxel-rollback /usr/local/bin/nuxel-diag-pack.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-diag-pack.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-diag-pack.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-diag-pack.sh)"
if [ -e /usr/local/bin/nuxel-diag-pack.sh ] && [ ! -e /usr/local/bin/nuxel-diag-pack.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-diag-pack.sh /usr/local/bin/nuxel-diag-pack.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-diag-pack.sh.nuxel-staged
printf '%s  %s\n' ecfc39e32783bd2803a14334395c3f3c165dd20b695dbde6f9df0bd1f2739e95 /usr/local/bin/nuxel-diag-pack.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-diag-pack.sh.nuxel-staged /usr/local/bin/nuxel-diag-pack.sh
sha256sum /usr/local/bin/nuxel-diag-pack.sh | grep -q ecfc39e32783bd2803a14334395c3f3c165dd20b695dbde6f9df0bd1f2739e95
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
