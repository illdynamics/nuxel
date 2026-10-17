#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/gnss/README.md (service: None, risk: medium)
# staged source: configs/nuxel/gnss/README.md
# previous-hash: dd26f110c8449196c1320a7ee4e02ea92ba010c621302125a9105b728c63cdeb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/gnss/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/README.md.nuxel-rollback /etc/nuxel/gnss/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/gnss/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/gnss/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/gnss/README.md)"
if [ -e /etc/nuxel/gnss/README.md ] && [ ! -e /etc/nuxel/gnss/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/gnss/README.md /etc/nuxel/gnss/README.md.nuxel-rollback; fi
test -f /etc/nuxel/gnss/README.md.nuxel-staged
printf '%s  %s\n' dd26f110c8449196c1320a7ee4e02ea92ba010c621302125a9105b728c63cdeb /etc/nuxel/gnss/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/gnss/README.md.nuxel-staged /etc/nuxel/gnss/README.md
sha256sum /etc/nuxel/gnss/README.md | grep -q dd26f110c8449196c1320a7ee4e02ea92ba010c621302125a9105b728c63cdeb
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
