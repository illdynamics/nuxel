#!/bin/sh
# S10+ a33 runtime tools, diagnostics and probes -> /usr/local/bin/nuxel-headphone-diag.sh (service: None, risk: medium)
# staged source: tools/s10plus/a33/nuxel-headphone-diag.sh
# previous-hash: 4fc2f6d993c1df631f8a19a8503d93572ea831ec2eb4298aad8d7c003229ff8f
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/local/bin/nuxel-headphone-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-headphone-diag.sh.nuxel-rollback /usr/local/bin/nuxel-headphone-diag.sh; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /usr/local/bin/nuxel-headphone-diag.sh ]; then printf 'PREV=%s\n' "$(sha256sum /usr/local/bin/nuxel-headphone-diag.sh | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/local/bin/nuxel-headphone-diag.sh)"
if [ -e /usr/local/bin/nuxel-headphone-diag.sh ] && [ ! -e /usr/local/bin/nuxel-headphone-diag.sh.nuxel-rollback ]; then cp -a /usr/local/bin/nuxel-headphone-diag.sh /usr/local/bin/nuxel-headphone-diag.sh.nuxel-rollback; fi
test -f /usr/local/bin/nuxel-headphone-diag.sh.nuxel-staged
printf '%s  %s\n' 4fc2f6d993c1df631f8a19a8503d93572ea831ec2eb4298aad8d7c003229ff8f /usr/local/bin/nuxel-headphone-diag.sh.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/local/bin/nuxel-headphone-diag.sh.nuxel-staged /usr/local/bin/nuxel-headphone-diag.sh
sha256sum /usr/local/bin/nuxel-headphone-diag.sh | grep -q 4fc2f6d993c1df631f8a19a8503d93572ea831ec2eb4298aad8d7c003229ff8f
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
