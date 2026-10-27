#!/bin/sh
# v0.7.1-beta bridge, notification and portal version pins -> /etc/systemd/system/nuxel-http-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-http-bridge.service
# previous-hash: 85427be3e66f1c6fcfdbbc1f02d8a1bbfbd1b65725e13d8b3c227a8b3b818e98
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 /etc/systemd/system/nuxel-http-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-http-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-http-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-http-bridge.service)"
if [ -e /etc/systemd/system/nuxel-http-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-http-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged
printf '%s  %s\n' 85427be3e66f1c6fcfdbbc1f02d8a1bbfbd1b65725e13d8b3c227a8b3b818e98 /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged /etc/systemd/system/nuxel-http-bridge.service
sha256sum /etc/systemd/system/nuxel-http-bridge.service | grep -q 85427be3e66f1c6fcfdbbc1f02d8a1bbfbd1b65725e13d8b3c227a8b3b818e98
echo INSTALL-OK
