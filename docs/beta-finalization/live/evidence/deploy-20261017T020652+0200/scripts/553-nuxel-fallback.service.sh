#!/bin/sh
# services/** runtime code, shims, units and D-Bus policies -> /etc/systemd/system/nuxel-fallback.service (service: None, risk: medium)
# staged source: services/nuxel-session/systemd/nuxel-fallback.service
# previous-hash: cbc1c5d18b365c7ecf7d544a7eb4932171cfef468429c3813df196adaca11233
set -u
_NXL_ROLLBACK() { _rc=$?; if [ "$_rc" -ne 0 ]; then if [ -e /etc/systemd/system/nuxel-fallback.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-fallback.service.nuxel-rollback /etc/systemd/system/nuxel-fallback.service; true; fi; echo "ROLLED-BACK rc=$_rc"; fi; }
trap _NXL_ROLLBACK EXIT
set -e
systemctl daemon-reload
if [ -e /etc/systemd/system/nuxel-fallback.service ]; then printf 'PREV=%s\n' "$(sha256sum /etc/systemd/system/nuxel-fallback.service | cut -d' ' -f1)"; else echo PREV=NONE; fi
mkdir -p "$(dirname /etc/systemd/system/nuxel-fallback.service)"
if [ -e /etc/systemd/system/nuxel-fallback.service ] && [ ! -e /etc/systemd/system/nuxel-fallback.service.nuxel-rollback ]; then cp -a /etc/systemd/system/nuxel-fallback.service /etc/systemd/system/nuxel-fallback.service.nuxel-rollback; fi
test -f /etc/systemd/system/nuxel-fallback.service.nuxel-staged
printf '%s  %s\n' cbc1c5d18b365c7ecf7d544a7eb4932171cfef468429c3813df196adaca11233 /etc/systemd/system/nuxel-fallback.service.nuxel-staged > /var/tmp/nxl-verify.sha256
sha256sum -c /var/tmp/nxl-verify.sha256
mv -f /etc/systemd/system/nuxel-fallback.service.nuxel-staged /etc/systemd/system/nuxel-fallback.service
sha256sum /etc/systemd/system/nuxel-fallback.service | grep -q cbc1c5d18b365c7ecf7d544a7eb4932171cfef468429c3813df196adaca11233
( systemctl daemon-reload && systemctl restart nuxel-bridge nuxel-http-bridge nuxel-portal nuxel-notifications ) || echo DECLARED-RELOAD-DEFERRED
systemctl daemon-reload
echo INSTALL-OK
