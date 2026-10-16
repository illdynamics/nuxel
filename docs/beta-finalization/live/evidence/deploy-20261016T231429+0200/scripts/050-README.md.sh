#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/security/README.md (service: None, risk: medium)
# staged source: configs/nuxel/security/README.md
# previous-hash: a3c64f1e57aae64790ca06e444c86ba4c570f6fb8819deb9006d4f1c52e98546
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/security/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/security/README.md.nuxel-rollback /etc/nuxel/security/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/security/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/security/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/security/README.md)"
if [ -e /etc/nuxel/security/README.md ] && [ ! -e /etc/nuxel/security/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/security/README.md /etc/nuxel/security/README.md.nuxel-rollback; fi
test -f /etc/nuxel/security/README.md.nuxel-staged
printf '%s  %s\n' a3c64f1e57aae64790ca06e444c86ba4c570f6fb8819deb9006d4f1c52e98546 /etc/nuxel/security/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/security/README.md.nuxel-staged /etc/nuxel/security/README.md
sha256sum /etc/nuxel/security/README.md | grep -q a3c64f1e57aae64790ca06e444c86ba4c570f6fb8819deb9006d4f1c52e98546
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
