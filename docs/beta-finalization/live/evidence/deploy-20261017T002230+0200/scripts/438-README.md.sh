#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/README.md (service: None, risk: medium)
# staged source: configs/nuxel/README.md
# previous-hash: 2871439d31e5c8f5c1adb36d5dc2e0b3680ed0364a78a6ea6b19254f3f88e387
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/README.md.nuxel-rollback /etc/nuxel/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/README.md)"
if [ -e /etc/nuxel/README.md ] && [ ! -e /etc/nuxel/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/README.md /etc/nuxel/README.md.nuxel-rollback; fi
test -f /etc/nuxel/README.md.nuxel-staged
printf '%s  %s\n' 2871439d31e5c8f5c1adb36d5dc2e0b3680ed0364a78a6ea6b19254f3f88e387 /etc/nuxel/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/README.md.nuxel-staged /etc/nuxel/README.md
sha256sum /etc/nuxel/README.md | grep -q 2871439d31e5c8f5c1adb36d5dc2e0b3680ed0364a78a6ea6b19254f3f88e387
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
