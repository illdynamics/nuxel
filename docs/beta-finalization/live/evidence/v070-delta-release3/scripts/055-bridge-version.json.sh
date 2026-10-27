#!/bin/sh
# systemd version pins and canonical bridge-version documents -> /usr/share/nuxel/pwa/nuxel-common/bridge-version.json (service: None, risk: medium)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: 33fc2c28c5265ef3bce984bfc274c587e4cc3aaa45005e2f6f43baa30cd498c5
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-v070-delta-release3 /usr/share/nuxel/pwa/nuxel-common/bridge-version.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge-version.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-v070-delta-release3 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-v070-delta-release3; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged
printf '%s  %s\n' 33fc2c28c5265ef3bce984bfc274c587e4cc3aaa45005e2f6f43baa30cd498c5 /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge-version.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | grep -q 33fc2c28c5265ef3bce984bfc274c587e4cc3aaa45005e2f6f43baa30cd498c5
echo INSTALL-OK
