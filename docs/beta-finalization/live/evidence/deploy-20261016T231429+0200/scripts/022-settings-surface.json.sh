#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/buttons/settings-surface.json (service: None, risk: medium)
# staged source: configs/nuxel/buttons/settings-surface.json
# previous-hash: 4c9533d8efd8faabfc991d69d9e21066fedc21a7483caec3fce48659c29f7e4c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/buttons/settings-surface.json.nuxel-rollback ]; then cp -a /etc/nuxel/buttons/settings-surface.json.nuxel-rollback /etc/nuxel/buttons/settings-surface.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/buttons/settings-surface.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/buttons/settings-surface.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/buttons/settings-surface.json)"
if [ -e /etc/nuxel/buttons/settings-surface.json ] && [ ! -e /etc/nuxel/buttons/settings-surface.json.nuxel-rollback ]; then cp -a /etc/nuxel/buttons/settings-surface.json /etc/nuxel/buttons/settings-surface.json.nuxel-rollback; fi
test -f /etc/nuxel/buttons/settings-surface.json.nuxel-staged
printf '%s  %s\n' 4c9533d8efd8faabfc991d69d9e21066fedc21a7483caec3fce48659c29f7e4c /etc/nuxel/buttons/settings-surface.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/buttons/settings-surface.json.nuxel-staged /etc/nuxel/buttons/settings-surface.json
sha256sum /etc/nuxel/buttons/settings-surface.json | grep -q 4c9533d8efd8faabfc991d69d9e21066fedc21a7483caec3fce48659c29f7e4c
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
