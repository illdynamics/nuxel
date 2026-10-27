#!/bin/sh
# v0.7.1-beta PWA version pins and launcher cache namespace -> /usr/share/nuxel/pwa/nuxel-common/bridge-version.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/bridge-version.json
# previous-hash: 6d756a9ab10c4370c7be75b1eba5f38cdaed86d44cb25784ff7d0779ff87de8a
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 /usr/share/nuxel/pwa/nuxel-common/bridge-version.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/bridge-version.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-rollback.pre-deploy-20261027T214523-2399095; fi
test -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged
printf '%s  %s\n' 6d756a9ab10c4370c7be75b1eba5f38cdaed86d44cb25784ff7d0779ff87de8a /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/bridge-version.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/bridge-version.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/bridge-version.json | grep -q 6d756a9ab10c4370c7be75b1eba5f38cdaed86d44cb25784ff7d0779ff87de8a
echo INSTALL-OK
