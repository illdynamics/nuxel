#!/bin/sh
# Nuxel Home + three Tri-Link PWA console entries -> /usr/share/nuxel/pwa/nuxel-common/app-registry.json (service: nuxel-web, risk: low)
# staged source: pwa/nuxel-common/app-registry.json
# previous-hash: 41cfaf09a1f501b61f55460894ed81f8acbda13c44ac4317401bd83a548ce030
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T163612-2117870 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T163612-2117870 /usr/share/nuxel/pwa/nuxel-common/app-registry.json; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json ]; then printf 'PREV=%s\n' "$(sha256sum /usr/share/nuxel/pwa/nuxel-common/app-registry.json | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /usr/share/nuxel/pwa/nuxel-common/app-registry.json)"
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback; fi
if [ -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json ] && [ ! -e /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T163612-2117870 ]; then cp -a /usr/share/nuxel/pwa/nuxel-common/app-registry.json /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-rollback.pre-deploy-20261027T163612-2117870; fi
test -f /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged
printf '%s  %s\n' 41cfaf09a1f501b61f55460894ed81f8acbda13c44ac4317401bd83a548ce030 /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /usr/share/nuxel/pwa/nuxel-common/app-registry.json.nuxel-staged /usr/share/nuxel/pwa/nuxel-common/app-registry.json
sha256sum /usr/share/nuxel/pwa/nuxel-common/app-registry.json | grep -q 41cfaf09a1f501b61f55460894ed81f8acbda13c44ac4317401bd83a548ce030
echo INSTALL-OK
