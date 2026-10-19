#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-notifications.service (service: None, risk: medium)
# staged source: services/nuxel-notifications/systemd/nuxel-notifications.service
# previous-hash: 76f28644e0421851d691525b35707695820b2d38168a2eb1a46aff81ca3e1ecb
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-notifications.service.nuxel-rollback /etc/systemd/system/nuxel-notifications.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-notifications.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-notifications.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-notifications.service)"
if [ -e /etc/systemd/system/nuxel-notifications.service ] && [ ! -e /etc/systemd/system/nuxel-notifications.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-notifications.service /etc/systemd/system/nuxel-notifications.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged
printf '%s  %s\n' 76f28644e0421851d691525b35707695820b2d38168a2eb1a46aff81ca3e1ecb /etc/systemd/system/nuxel-notifications.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-notifications.service.nuxel-staged /etc/systemd/system/nuxel-notifications.service
sha256sum /etc/systemd/system/nuxel-notifications.service | grep -q 76f28644e0421851d691525b35707695820b2d38168a2eb1a46aff81ca3e1ecb
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
