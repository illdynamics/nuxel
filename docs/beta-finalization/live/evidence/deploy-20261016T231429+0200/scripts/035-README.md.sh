#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/keyboard/README.md (service: None, risk: medium)
# staged source: configs/nuxel/keyboard/README.md
# previous-hash: 6dc324dd4d1961f8e10e1a158afb531f23db652f8443d13cc6f5a5bb0d06e728
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/keyboard/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/keyboard/README.md.nuxel-rollback /etc/nuxel/keyboard/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/keyboard/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/keyboard/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/keyboard/README.md)"
if [ -e /etc/nuxel/keyboard/README.md ] && [ ! -e /etc/nuxel/keyboard/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/keyboard/README.md /etc/nuxel/keyboard/README.md.nuxel-rollback; fi
test -f /etc/nuxel/keyboard/README.md.nuxel-staged
printf '%s  %s\n' 6dc324dd4d1961f8e10e1a158afb531f23db652f8443d13cc6f5a5bb0d06e728 /etc/nuxel/keyboard/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/keyboard/README.md.nuxel-staged /etc/nuxel/keyboard/README.md
sha256sum /etc/nuxel/keyboard/README.md | grep -q 6dc324dd4d1961f8e10e1a158afb531f23db652f8443d13cc6f5a5bb0d06e728
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
