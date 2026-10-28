#!/bin/sh
# Decouple launcher chain from network-online/network.target -> /etc/systemd/system/nuxel-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-bridge.service
# previous-hash: 23a90fe9eeb6497fd1aad3cbcadae618e41003246c2dc56c4e24916035ec2fb8
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261028T095312-2716758 ]; then cp -a /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261028T095312-2716758 /etc/systemd/system/nuxel-bridge.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bridge.service)"
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261028T095312-2716758 ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback.pre-deploy-20261028T095312-2716758; fi
test -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged
printf '%s  %s\n' 23a90fe9eeb6497fd1aad3cbcadae618e41003246c2dc56c4e24916035ec2fb8 /etc/systemd/system/nuxel-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged /etc/systemd/system/nuxel-bridge.service
sha256sum /etc/systemd/system/nuxel-bridge.service | grep -q 23a90fe9eeb6497fd1aad3cbcadae618e41003246c2dc56c4e24916035ec2fb8
echo INSTALL-OK
