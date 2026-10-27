#!/bin/sh
# systemd version pins and canonical bridge-version documents -> /etc/nuxel/bridge-version.json (service: None, risk: medium)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: 33fc2c28c5265ef3bce984bfc274c587e4cc3aaa45005e2f6f43baa30cd498c5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/bridge-version.json.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /etc/nuxel/bridge-version.json.nuxel-rollback.pre-v070-delta-release2 /etc/nuxel/bridge-version.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/bridge-version.json)"
if [ -e /etc/nuxel/bridge-version.json ] && [ ! -e /etc/nuxel/bridge-version.json.nuxel-rollback ]; then cp -a /etc/nuxel/bridge-version.json /etc/nuxel/bridge-version.json.nuxel-rollback; fi
if [ -e /etc/nuxel/bridge-version.json ] && [ ! -e /etc/nuxel/bridge-version.json.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /etc/nuxel/bridge-version.json /etc/nuxel/bridge-version.json.nuxel-rollback.pre-v070-delta-release2; fi
test -f /etc/nuxel/bridge-version.json.nuxel-staged
printf '%s  %s\n' 33fc2c28c5265ef3bce984bfc274c587e4cc3aaa45005e2f6f43baa30cd498c5 /etc/nuxel/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bridge-version.json.nuxel-staged /etc/nuxel/bridge-version.json
sha256sum /etc/nuxel/bridge-version.json | grep -q 33fc2c28c5265ef3bce984bfc274c587e4cc3aaa45005e2f6f43baa30cd498c5
echo INSTALL-OK
