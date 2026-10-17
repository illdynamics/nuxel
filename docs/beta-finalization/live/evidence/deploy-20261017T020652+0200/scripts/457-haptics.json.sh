#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/haptics/haptics.json (service: None, risk: medium)
# staged source: configs/nuxel/haptics/haptics.json
# previous-hash: c3966b4a23b5054a90b1ebe1727630f37bf8d65b76cd5a522bd4089852248d40
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/haptics/haptics.json.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/haptics.json.nuxel-rollback /etc/nuxel/haptics/haptics.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/haptics/haptics.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/haptics/haptics.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/haptics/haptics.json)"
if [ -e /etc/nuxel/haptics/haptics.json ] && [ ! -e /etc/nuxel/haptics/haptics.json.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/haptics.json /etc/nuxel/haptics/haptics.json.nuxel-rollback; fi
test -f /etc/nuxel/haptics/haptics.json.nuxel-staged
printf '%s  %s\n' c3966b4a23b5054a90b1ebe1727630f37bf8d65b76cd5a522bd4089852248d40 /etc/nuxel/haptics/haptics.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/haptics/haptics.json.nuxel-staged /etc/nuxel/haptics/haptics.json
sha256sum /etc/nuxel/haptics/haptics.json | grep -q c3966b4a23b5054a90b1ebe1727630f37bf8d65b76cd5a522bd4089852248d40
( systemctl daemon-reload ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
