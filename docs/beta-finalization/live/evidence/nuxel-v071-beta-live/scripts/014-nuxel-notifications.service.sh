#!/bin/sh
# v0.7.1-beta bridge, notification and portal version pins -> /etc/systemd/system/nuxel-notifications.service (service: None, risk: medium)
# staged source: services/nuxel-notifications/systemd/nuxel-notifications.service
# previous-hash: 81baaef33731ee6f5cb6caec5b61720e8f048a1ee9b402d1c0d3abba872c62f2
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 /etc/systemd/system/nuxel-notifications.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-notifications.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-notifications.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-notifications.service)"
if [ -e /etc/systemd/system/nuxel-notifications.service ] && [ ! -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-notifications.service /etc/systemd/system/nuxel-notifications.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-notifications.service ] && [ ! -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-deploy-20261027T214530-2399261 ]; then cp -a /etc/systemd/system/nuxel-notifications.service /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-deploy-20261027T214530-2399261; fi
test -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged
printf '%s  %s\n' 81baaef33731ee6f5cb6caec5b61720e8f048a1ee9b402d1c0d3abba872c62f2 /etc/systemd/system/nuxel-notifications.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged /etc/systemd/system/nuxel-notifications.service
sha256sum /etc/systemd/system/nuxel-notifications.service | grep -q 81baaef33731ee6f5cb6caec5b61720e8f048a1ee9b402d1c0d3abba872c62f2
echo INSTALL-OK
