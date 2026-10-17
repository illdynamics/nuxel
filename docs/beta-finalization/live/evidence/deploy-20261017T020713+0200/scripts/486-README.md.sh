#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/touch/README.md (service: nuxel-touch-arm, risk: medium)
# staged source: configs/nuxel/touch/README.md
# previous-hash: dd8228b3397c0a6b811bf478ee754281a7b3f6deae921cc4292074c9c6c5522c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/touch/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/touch/README.md.nuxel-rollback /etc/nuxel/touch/README.md; systemctl restart nuxel-touch-arm; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/touch/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/touch/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/touch/README.md)"
if [ -e /etc/nuxel/touch/README.md ] && [ ! -e /etc/nuxel/touch/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/touch/README.md /etc/nuxel/touch/README.md.nuxel-rollback; fi
test -f /etc/nuxel/touch/README.md.nuxel-staged
printf '%s  %s\n' dd8228b3397c0a6b811bf478ee754281a7b3f6deae921cc4292074c9c6c5522c /etc/nuxel/touch/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/touch/README.md.nuxel-staged /etc/nuxel/touch/README.md
sha256sum /etc/nuxel/touch/README.md | grep -q dd8228b3397c0a6b811bf478ee754281a7b3f6deae921cc4292074c9c6c5522c
systemctl restart nuxel-touch-arm
systemctl is-active nuxel-touch-arm
systemctl daemon-reload
echo INSTALL-OK
