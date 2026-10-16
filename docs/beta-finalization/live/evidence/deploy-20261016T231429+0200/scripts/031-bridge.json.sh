#!/bin/sh
# remaining /etc/nuxel documents and unit files -> /etc/nuxel/haptics/bridge.json (service: None, risk: medium)
# staged source: configs/nuxel/haptics/bridge.json
# previous-hash: c07935b0bd18e6f865675a9a269decd5d998c1da68b6d79492e704e5d266009d
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/haptics/bridge.json.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/bridge.json.nuxel-rollback /etc/nuxel/haptics/bridge.json; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/nuxel/haptics/bridge.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/haptics/bridge.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/haptics/bridge.json)"
if [ -e /etc/nuxel/haptics/bridge.json ] && [ ! -e /etc/nuxel/haptics/bridge.json.nuxel-rollback ]; then cp -a /etc/nuxel/haptics/bridge.json /etc/nuxel/haptics/bridge.json.nuxel-rollback; fi
test -f /etc/nuxel/haptics/bridge.json.nuxel-staged
printf '%s  %s\n' c07935b0bd18e6f865675a9a269decd5d998c1da68b6d79492e704e5d266009d /etc/nuxel/haptics/bridge.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/haptics/bridge.json.nuxel-staged /etc/nuxel/haptics/bridge.json
sha256sum /etc/nuxel/haptics/bridge.json | grep -q c07935b0bd18e6f865675a9a269decd5d998c1da68b6d79492e704e5d266009d
systemctl daemon-reload
systemctl daemon-reload
echo INSTALL-OK
