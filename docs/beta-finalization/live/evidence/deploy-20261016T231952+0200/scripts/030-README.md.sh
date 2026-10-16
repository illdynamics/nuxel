#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/haptics/README.md (service: None, risk: medium)
# staged source: configs/nuxel/haptics/README.md
# previous-hash: 12560ef110c7503b43a8741c7cc282a76bc45ec64c540ff982992958e5c077b7
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/haptics/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/README.md.nuxel-rollback /etc/nuxel/haptics/README.md; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/haptics/README.md ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/haptics/README.md | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/haptics/README.md)"
if [ -e /etc/nuxel/haptics/README.md ] && [ ! -e /etc/nuxel/haptics/README.md.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/README.md /etc/nuxel/haptics/README.md.nuxel-rollback; fi
test -f /etc/nuxel/haptics/README.md.nuxel-staged
printf '%s  %s\n' 12560ef110c7503b43a8741c7cc282a76bc45ec64c540ff982992958e5c077b7 /etc/nuxel/haptics/README.md.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/haptics/README.md.nuxel-staged /etc/nuxel/haptics/README.md
sha256sum /etc/nuxel/haptics/README.md | grep -q 12560ef110c7503b43a8741c7cc282a76bc45ec64c540ff982992958e5c077b7
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
