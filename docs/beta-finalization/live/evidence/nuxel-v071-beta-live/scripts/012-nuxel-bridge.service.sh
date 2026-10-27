#!/bin/sh
# v0.7.1-beta bridge, notification and portal version pins -> /etc/systemd/system/nuxel-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-bridge.service
# previous-hash: b0258b6fc11f379870532806d61f190f2705c7af6ad171ba7f567c08023dca2c
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 /etc/systemd/system/nuxel-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bridge.service)"
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged
printf '%s  %s\n' b0258b6fc11f379870532806d61f190f2705c7af6ad171ba7f567c08023dca2c /etc/systemd/system/nuxel-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged /etc/systemd/system/nuxel-bridge.service
sha256sum /etc/systemd/system/nuxel-bridge.service | grep -q b0258b6fc11f379870532806d61f190f2705c7af6ad171ba7f567c08023dca2c
echo INSTALL-OK
