#!/bin/sh
# Decouple launcher chain from network-online/network.target -> /etc/systemd/system/nuxel-web.service (service: None, risk: medium)
# staged source: services/nuxel-web.service
# previous-hash: dfee7a3807d687ea5ff8edc653f84ee46241e9c96c1298c07e7a5188ff00c8a4
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-web.service.nuxel-rollback.pre-deploy-20261028T095312-2716758 ]; then cp -a /etc/systemd/system/nuxel-web.service.nuxel-rollback.pre-deploy-20261028T095312-2716758 /etc/systemd/system/nuxel-web.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-web.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-web.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-web.service)"
if [ -e /etc/systemd/system/nuxel-web.service ] && [ ! -e /etc/systemd/system/nuxel-web.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-web.service /etc/systemd/system/nuxel-web.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-web.service ] && [ ! -e /etc/systemd/system/nuxel-web.service.nuxel-rollback.pre-deploy-20261028T095312-2716758 ]; then cp -a /etc/systemd/system/nuxel-web.service /etc/systemd/system/nuxel-web.service.nuxel-rollback.pre-deploy-20261028T095312-2716758; fi
test -f /etc/systemd/system/nuxel-web.service.nuxel-staged
printf '%s  %s\n' dfee7a3807d687ea5ff8edc653f84ee46241e9c96c1298c07e7a5188ff00c8a4 /etc/systemd/system/nuxel-web.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-web.service.nuxel-staged /etc/systemd/system/nuxel-web.service
sha256sum /etc/systemd/system/nuxel-web.service | grep -q dfee7a3807d687ea5ff8edc653f84ee46241e9c96c1298c07e7a5188ff00c8a4
echo INSTALL-OK
