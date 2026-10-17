#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-security-audit.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-security-audit.sh
# previous-hash: f29e44796822b4119ee6b7fefa0cb77d87c3065ab3ef6e80dc93770e338bb551
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-security-audit.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-security-audit.sh.nuxel-rollback /usr/local/bin/nuxel-security-audit.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-security-audit.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-security-audit.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-security-audit.sh)"
if [ -e /usr/local/bin/nuxel-security-audit.sh ] && [ ! -e /usr/local/bin/nuxel-security-audit.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-security-audit.sh /usr/local/bin/nuxel-security-audit.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-security-audit.sh.nuxel-staged
printf '%s  %s\n' f29e44796822b4119ee6b7fefa0cb77d87c3065ab3ef6e80dc93770e338bb551 /usr/local/bin/nuxel-security-audit.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-security-audit.sh.nuxel-staged /usr/local/bin/nuxel-security-audit.sh
sha256sum /usr/local/bin/nuxel-security-audit.sh | grep -q f29e44796822b4119ee6b7fefa0cb77d87c3065ab3ef6e80dc93770e338bb551
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
