#!/bin/sh
# systemd unit env pins + bridge-version.json + shared PWA bridge honesty fallback -> /etc/nuxel/bridge-version.json (service: None, risk: medium)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: 4d9710dd847789380761c118185c84d5593ed9c829f4a852402780f5ec3876de
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/bridge-version.json.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000 ]; then cp -a /etc/nuxel/bridge-version.json.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000 /etc/nuxel/bridge-version.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/bridge-version.json)"
if [ -e /etc/nuxel/bridge-version.json ] && [ ! -e /etc/nuxel/bridge-version.json.nuxel-rollback ]; then cp -a /etc/nuxel/bridge-version.json /etc/nuxel/bridge-version.json.nuxel-rollback; fi
if [ -e /etc/nuxel/bridge-version.json ] && [ ! -e /etc/nuxel/bridge-version.json.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000 ]; then cp -a /etc/nuxel/bridge-version.json /etc/nuxel/bridge-version.json.nuxel-rollback.pre-a75-bridge-version-restore-recover-n25000; fi
test -f /etc/nuxel/bridge-version.json.nuxel-staged
printf '%s  %s\n' 4d9710dd847789380761c118185c84d5593ed9c829f4a852402780f5ec3876de /etc/nuxel/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bridge-version.json.nuxel-staged /etc/nuxel/bridge-version.json
sha256sum /etc/nuxel/bridge-version.json | grep -q 4d9710dd847789380761c118185c84d5593ed9c829f4a852402780f5ec3876de
echo INSTALL-OK
