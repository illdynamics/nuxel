#!/bin/sh
# Decouple launcher chain from network-online/network.target -> /etc/systemd/system/nuxel-portal.service (service: None, risk: medium)
# staged source: services/nuxel-portal/systemd/nuxel-portal.service
# previous-hash: d113c2e5a7be5ad9a0d1ad36170a520c3319a9c22ec18246b2822c6c46fb0b94
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-portal.service.nuxel-rollback.pre-deploy-20261028T100542-2722856 ]; then cp -a /etc/systemd/system/nuxel-portal.service.nuxel-rollback.pre-deploy-20261028T100542-2722856 /etc/systemd/system/nuxel-portal.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-portal.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-portal.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-portal.service)"
if [ -e /etc/systemd/system/nuxel-portal.service ] && [ ! -e /etc/systemd/system/nuxel-portal.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-portal.service /etc/systemd/system/nuxel-portal.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-portal.service ] && [ ! -e /etc/systemd/system/nuxel-portal.service.nuxel-rollback.pre-deploy-20261028T100542-2722856 ]; then cp -a /etc/systemd/system/nuxel-portal.service /etc/systemd/system/nuxel-portal.service.nuxel-rollback.pre-deploy-20261028T100542-2722856; fi
test -f /etc/systemd/system/nuxel-portal.service.nuxel-staged
printf '%s  %s\n' d113c2e5a7be5ad9a0d1ad36170a520c3319a9c22ec18246b2822c6c46fb0b94 /etc/systemd/system/nuxel-portal.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-portal.service.nuxel-staged /etc/systemd/system/nuxel-portal.service
sha256sum /etc/systemd/system/nuxel-portal.service | grep -q d113c2e5a7be5ad9a0d1ad36170a520c3319a9c22ec18246b2822c6c46fb0b94
echo INSTALL-OK
