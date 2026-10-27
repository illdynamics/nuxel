#!/bin/sh
# systemd version pins and canonical bridge-version documents -> /etc/systemd/system/nuxel-notifications.service (service: None, risk: medium)
# staged source: services/nuxel-notifications/systemd/nuxel-notifications.service
# previous-hash: e7918f28419c23cc210d39fa782c7cd603a18353f7bfe730f98ad8369a5382cd
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-v070-delta-release2 /etc/systemd/system/nuxel-notifications.service; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
if [ -e /etc/systemd/system/nuxel-notifications.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-notifications.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-notifications.service)"
if [ -e /etc/systemd/system/nuxel-notifications.service ] && [ ! -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-notifications.service /etc/systemd/system/nuxel-notifications.service.nuxel-rollback; fi
if [ -e /etc/systemd/system/nuxel-notifications.service ] && [ ! -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-v070-delta-release2 ]; then cp -a /etc/systemd/system/nuxel-notifications.service /etc/systemd/system/nuxel-notifications.service.nuxel-rollback.pre-v070-delta-release2; fi
test -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged
printf '%s  %s\n' e7918f28419c23cc210d39fa782c7cd603a18353f7bfe730f98ad8369a5382cd /etc/systemd/system/nuxel-notifications.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged /etc/systemd/system/nuxel-notifications.service
sha256sum /etc/systemd/system/nuxel-notifications.service | grep -q e7918f28419c23cc210d39fa782c7cd603a18353f7bfe730f98ad8369a5382cd
echo INSTALL-OK
