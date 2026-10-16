#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/time/README.md (service: None, risk: medium)
# staged source: configs/nuxel/time/README.md
# previous-hash: 8de48671320ac022111cb112b80cc7ce7f752489e5274ad2e576864dcbbbc14c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/time/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/time/README.md.nuxel-rollback /etc/nuxel/time/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/time/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/time/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/time/README.md)"
if [ -e /etc/nuxel/time/README.md ] && [ ! -e /etc/nuxel/time/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/time/README.md /etc/nuxel/time/README.md.nuxel-rollback; fi
test -f /etc/nuxel/time/README.md.nuxel-staged
printf '%s  %s\n' 8de48671320ac022111cb112b80cc7ce7f752489e5274ad2e576864dcbbbc14c /etc/nuxel/time/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/time/README.md.nuxel-staged /etc/nuxel/time/README.md
sha256sum /etc/nuxel/time/README.md | grep -q 8de48671320ac022111cb112b80cc7ce7f752489e5274ad2e576864dcbbbc14c
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
