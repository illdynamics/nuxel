#!/bin/sh
# v0.7.1-beta bridge, notification and portal version pins -> /etc/nuxel/bridge-version.json (service: None, risk: medium)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: 6d756a9ab10c4370c7be75b1eba5f38cdaed86d44cb25784ff7d0779ff87de8a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/nuxel/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /etc/nuxel/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 /etc/nuxel/bridge-version.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/nuxel/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /etc/nuxel/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/nuxel/bridge-version.json)"
if [ -e /etc/nuxel/bridge-version.json ] && [ ! -e /etc/nuxel/bridge-version.json.nuxel-rollback ]; then cp -a /etc/nuxel/bridge-version.json /etc/nuxel/bridge-version.json.nuxel-rollback; fi
if [ -e /etc/nuxel/bridge-version.json ] && [ ! -e /etc/nuxel/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /etc/nuxel/bridge-version.json /etc/nuxel/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095; fi
test -f /etc/nuxel/bridge-version.json.nuxel-staged
printf '%s  %s\n' 6d756a9ab10c4370c7be75b1eba5f38cdaed86d44cb25784ff7d0779ff87de8a /etc/nuxel/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/nuxel/bridge-version.json.nuxel-staged /etc/nuxel/bridge-version.json
sha256sum /etc/nuxel/bridge-version.json | grep -q 6d756a9ab10c4370c7be75b1eba5f38cdaed86d44cb25784ff7d0779ff87de8a
echo INSTALL-OK
