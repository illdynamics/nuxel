#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-notifications.service (service: None, risk: medium)
# staged source: services/nuxel-notifications/systemd/nuxel-notifications.service
# previous-hash: 275b2ea2f3d789bcf9ceda404bbb82b70b3e7e594c6a731b257deb98b6c1f181
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-notifications.service.nuxel-rollback /etc/systemd/system/nuxel-notifications.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-notifications.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-notifications.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-notifications.service)"
if [ -e /etc/systemd/system/nuxel-notifications.service ] && [ ! -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-notifications.service /etc/systemd/system/nuxel-notifications.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged
printf '%s  %s\n' 275b2ea2f3d789bcf9ceda404bbb82b70b3e7e594c6a731b257deb98b6c1f181 /etc/systemd/system/nuxel-notifications.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged /etc/systemd/system/nuxel-notifications.service
sha256sum /etc/systemd/system/nuxel-notifications.service | grep -q 275b2ea2f3d789bcf9ceda404bbb82b70b3e7e594c6a731b257deb98b6c1f181
systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications
systemctl daemon-reload
echo INSTALL-OK
