#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-http-bridge.service (service: None, risk: medium)
# staged source: services/nuxel-bridge/systemd/nuxel-http-bridge.service
# previous-hash: 863a812e5da7e1e01cf7248d2403e754fed8e0d2ab9381c93e3e65af6e3f3898
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback /etc/systemd/system/nuxel-http-bridge.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-http-bridge.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-http-bridge.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-http-bridge.service)"
if [ -e /etc/systemd/system/nuxel-http-bridge.service ] && [ ! -e /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-http-bridge.service /etc/systemd/system/nuxel-http-bridge.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged
printf '%s  %s\n' 863a812e5da7e1e01cf7248d2403e754fed8e0d2ab9381c93e3e65af6e3f3898 /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-http-bridge.service.nuxel-staged /etc/systemd/system/nuxel-http-bridge.service
sha256sum /etc/systemd/system/nuxel-http-bridge.service | grep -q 863a812e5da7e1e01cf7248d2403e754fed8e0d2ab9381c93e3e65af6e3f3898
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
