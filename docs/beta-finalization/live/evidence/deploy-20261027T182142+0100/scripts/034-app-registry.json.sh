#!/bin/sh
# Nuxel Home, Settings, Maps and the three Tri-Link consoles -> /usr/share/nuxel/pwa/nuxel-common/app-registry.json (service: None, risk: low)
# staged source: pwa/nuxel-common/app-registry.json
# previous-hash: bae591391417121a5933ff3b2504bf26af634aa9b7d2e584bec9d28a506996c1
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 /usr/share/nuxel/pwa/nuxel-common/app-registry.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/app-registry.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/app-registry.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T182142-2202036 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T182142-2202036; fi
test -f /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged
printf '%s  %s\n' bae591391417121a5933ff3b2504bf26af634aa9b7d2e584bec9d28a506996c1 /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/app-registry.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/app-registry.json | grep -q bae591391417121a5933ff3b2504bf26af634aa9b7d2e584bec9d28a506996c1
echo INSTALL-OK
