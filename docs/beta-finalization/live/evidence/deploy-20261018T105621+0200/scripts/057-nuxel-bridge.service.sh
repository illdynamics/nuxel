#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-bridge.service
# previous-hash: b8f21cc16f1494a805184fae349a0ac725d91150272fcfc42f3ee320685c6d6e
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bridge.service.nuxel-rollback /etc/systemd/system/nuxel-bridge.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-bridge.service)"
if [ -e /etc/systemd/system/nuxel-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-bridge.service /etc/systemd/system/nuxel-bridge.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged
printf '%s  %s\n' b8f21cc16f1494a805184fae349a0ac725d91150272fcfc42f3ee320685c6d6e /etc/systemd/system/nuxel-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-bridge.service.nuxel-staged /etc/systemd/system/nuxel-bridge.service
sha256sum /etc/systemd/system/nuxel-bridge.service | grep -q b8f21cc16f1494a805184fae349a0ac725d91150272fcfc42f3ee320685c6d6e
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
